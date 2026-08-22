terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Configure Google Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "cloudrun" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

# Get current project configuration
data "google_client_config" "default" {}

# Create Artifact Registry repository
resource "google_artifact_registry_repository" "app" {
  location      = var.region
  repository_id = var.service_name
  format        = "DOCKER"
  description   = "Docker repository for ${var.service_name}"
}

locals {
  registry_host = "${var.region}-docker.pkg.dev"
  app_image     = "${local.registry_host}/${var.project_id}/${var.service_name}/${var.service_name}:${var.docker_image_tag}"
  build_context = abspath("${path.module}/../..")

  # Hash of everything baked into the image, so a code change forces a rebuild.
  source_hash = sha1(join("", [
    for f in sort(tolist(setunion(
      fileset(local.build_context, "Dockerfile"),
      fileset(local.build_context, "backend/**"),
      fileset(local.build_context, "frontend/src/**"),
      fileset(local.build_context, "frontend/package*.json"),
      fileset(local.build_context, "frontend/*.ts"),
      fileset(local.build_context, "frontend/*.mjs"),
      fileset(local.build_context, "frontend/*.json"),
    ))) : filesha1("${local.build_context}/${f}")
  ]))
}

# Built via buildx rather than the kreuzwerker provider, whose legacy build API
# corrupts the context on cross-platform (arm64 host -> linux/amd64) builds.
resource "null_resource" "docker_build_push" {
  triggers = {
    source_hash = local.source_hash
    image       = local.app_image
  }

  provisioner "local-exec" {
    working_dir = local.build_context
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      gcloud auth configure-docker '${local.registry_host}' --quiet
      docker buildx build \
        --platform linux/amd64 \
        --tag '${local.app_image}' \
        --push \
        .
    EOT
  }

  depends_on = [
    google_project_service.cloudbuild,
    google_artifact_registry_repository.app
  ]
}

# Deploy to Cloud Run
resource "google_cloud_run_service" "app" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = local.app_image

        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi" # 2GB required for Semgrep MCP server
          }
        }

        env {
          name  = "OPENAI_API_KEY"
          value = var.openai_api_key
        }

        env {
          name  = "SEMGREP_APP_TOKEN"
          value = var.semgrep_app_token
        }

        env {
          name  = "ENVIRONMENT"
          value = "production"
        }

        env {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        }

        ports {
          container_port = 8000
        }
      }
    }

    metadata {
      # The :latest tag never changes, so tie the revision to image content.
      name = "${var.service_name}-${substr(local.source_hash, 0, 10)}"

      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "1"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }


  depends_on = [
    google_project_service.cloudrun,
    null_resource.docker_build_push
  ]
}

# Make the service publicly accessible
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.app.name
  location = google_cloud_run_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "service_url" {
  value       = google_cloud_run_service.app.status[0].url
  description = "URL of the deployed Cloud Run service"
}

output "project_id" {
  value       = var.project_id
  description = "GCP Project ID"
}

output "region" {
  value       = var.region
  description = "GCP region"
}
