# Week 3 Day 1: `terraform apply` fails on `docker_image.app` with "unpigz: corrupted"

Contributed by Kirsten (Udemy lecture 69, August 2026). Reproduced on one machine only;
see "How widely does this apply" at the bottom before assuming it is your problem too.

## Symptom

`terraform apply` in `terraform/azure` (and `terraform/gcp`, which has the same resource)
dies while building the image:

```
Error running legacy build: failed to read dockerfile: exit status 1:
unpigz: skipping: <stdin>: corrupted -- invalid deflate data
```

The exact wording varies between attempts: `invalid code lengths set`,
`invalid stored block lengths`, `invalid block type`. Nothing is actually corrupted, which
is why the word "corrupted" sends you hunting in the wrong place.

## The fix

Add `builder = "default"` to the `build` block, and make `dockerfile` a full path:

```hcl
build {
  context    = "${path.module}/../.."
  dockerfile = "${path.module}/../../Dockerfile"
  builder    = "default"
  ...
}
```

That is the whole fix. A 1.2 GB context then builds and pushes in about 47 seconds.

Note the second line as well. On this code path `dockerfile` is resolved relative to the
Terraform working directory instead of relative to `context`. Leave it as plain
`Dockerfile` and you get `open Dockerfile: no such file or directory`, which looks like a
missing file but is a path issue.

## The cause

The daemon truncates the build context when two things coincide: the BuildKit endpoint
(`POST /build?version=2`) and a request body sent with `Transfer-Encoding: chunked`.
Past roughly 430 KB the rest never arrives. `unpigz` then receives half a gzip stream and
reports exactly that. It is the messenger, not the culprit.

The Terraform provider uses precisely that combination. The Docker CLI never does, which
is why `docker build` on the same context works fine.

`builder = "default"` switches the provider to its buildx code path, where the context
travels over a session instead of a chunked body, so the truncation never happens.

## How this was established

With a proxy sitting between the provider and `/var/run/docker.sock`, recording what the
provider actually sends:

| endpoint | framing | result |
| --- | --- | --- |
| `version=1` (legacy) | Content-Length | ok |
| `version=1` (legacy) | chunked | ok |
| `version=2` (BuildKit) | Content-Length | ok |
| `version=2` (BuildKit) | chunked | FAIL |

With an uncompressed tar, that same failing cell reports `failed to read dockerfile:
unexpected EOF`, which is the truncation without gzip in between. The boundary is sharp:
a tar of 409,600 bytes builds, 460,800 bytes does not.

## What it is not

All of these were measured, not assumed:

- Not a corrupt gzip from the provider. The captured stream decompresses completely:
  one member, cleanly terminated, 1,051,136 bytes out.
- Not `unpigz` choking on that stream. Fed to it by hand, no complaint.
- Not chunk size. The provider sends 262 chunks, 62 of them a single byte; replaying that
  exact pattern succeeds, while one single 1 MB chunk fails.
- Not timing. A 0.1 second pause between chunks fails just the same.
- Not disk space, `.dockerignore`, odd files in the context, or the provider version
  (3.9.0, 3.6.2 and 3.2.0 fail identically).

Two knobs that look like they should help and do nothing: `version = "1"` in the build
block, and `DOCKER_BUILDKIT=0` in the environment. The provider sends `version=2` either
way.

Docker Desktop's WSL relay is not the culprit either. It moves bytes and does not read the
query parameter, and `version=1` chunked works over that same socket while `version=2`
chunked fails. So the difference has to sit in the daemon handler. What exactly goes wrong
inside moby's builder-next was not read in the source; that part remains a hypothesis.

## How widely does this apply

Unknown, and worth saying plainly. Measured on one machine only:

- WSL2, Docker Desktop 4.83.0, engine 29.6.2 (built 2026-07-16)
- Terraform Docker provider 3.9.0 (also tried 3.6.2 and 3.2.0)

A second machine, a second engine version and a bare `dockerd` were not tested. The course
was clearly recorded with a working provider, so this is not universal. A regression in a
recent engine would fit both observations, but that is a hypothesis, not a finding. If it
does turn out to be version dependent, it will spread as students update Docker, which is
why it seemed worth writing down.
