# Day 2 Part 2: Google Cloud Platform

This guide will deploy the Cybersecurity Analyzer to Google Cloud Run using Terraform. The deployment will automatically build your Docker image, push it to Google Container Registry, and deploy it as a serverless container application.

## Prerequisites

✅ Complete the [GCP Setup Guide](./setup_gcp.md) first
✅ Terraform CLI installed (covered in previous course modules)
✅ Docker running locally
✅ `.env` file in project root with your API keys
✅ Note your GCP Project ID (e.g., `cyber-analyzer-123456`)

## Quick Terraform Check

If you missed the Terraform installation from previous modules:

```bash
# Check if Terraform is installed
terraform version

# If not installed:
# Mac: brew install terraform
# Windows: Download from https://terraform.io/downloads
# Linux: See https://terraform.io/docs/cli/install/apt.html
```

---

## Step 1: Get Your Project ID

You'll need your GCP Project ID (not the project name). Find it:

```bash
# List your projects and their IDs
gcloud projects list

# Should show something like:
# PROJECT_ID              NAME            PROJECT_NUMBER
# cyber-analyzer-123456   cyber-analyzer  123456789012
```

Copy your PROJECT_ID - you'll need it in the next steps.

---

## Step 2: Set Environment Variables

Terraform will read your API keys and project ID from environment variables. We'll load them from your `.env` file:

### Mac/Linux:
```bash
# Load environment variables from .env file
export $(cat .env | xargs)

# Set your GCP Project ID (replace with your actual ID)
export TF_VAR_project_id="cyber-analyzer-123456"

# Verify they're loaded
echo "Project ID: $TF_VAR_project_id"
echo "OpenAI key loaded: ${OPENAI_API_KEY:0:8}..."
echo "Semgrep token loaded: ${SEMGREP_APP_TOKEN:0:8}..."
```

### Windows (PowerShell):
```powershell
# Load environment variables from .env file
Get-Content .env | ForEach-Object {
    $name, $value = $_.split('=', 2)
    Set-Item -Path "env:$name" -Value $value
}

# Set your GCP Project ID (replace with your actual ID)
$env:TF_VAR_project_id = "cyber-analyzer-123456"

# Verify they're loaded
Write-Host "Project ID: $env:TF_VAR_project_id"
Write-Host "OpenAI key loaded: $($env:OPENAI_API_KEY.Substring(0,8))..."
Write-Host "Semgrep token loaded: $($env:SEMGREP_APP_TOKEN.Substring(0,8))..."
```

---

## Step 3: Initialize Terraform

Navigate to the GCP Terraform configuration:

```bash
cd terraform/gcp
```

Initialize Terraform and create a GCP workspace:

```bash
# Initialize Terraform
terraform init

# Create and select GCP workspace
terraform workspace new gcp
terraform workspace select gcp

# Verify you're in the right workspace
terraform workspace show
```

You should see output showing the Google provider being downloaded and the workspace set to `gcp`.

---

## Step 4: Authenticate with Google Cloud

Ensure you're authenticated and have the right project selected:

```bash
# Login to Google Cloud (will open browser)
gcloud auth login

# Set your project
gcloud config set project $TF_VAR_project_id

# Get application default credentials for Terraform
gcloud auth application-default login

# Align the quota project (prevents warning messages)
gcloud auth application-default set-quota-project $TF_VAR_project_id

# Configure Docker to use gcloud credentials (required for pushing images)
gcloud auth configure-docker

# Verify authentication
gcloud config list
```

Make sure the project shown matches your PROJECT_ID.

> **Note**: When running `gcloud auth configure-docker`, you'll be asked to update your Docker config. Type 'Y' to confirm.

---

## Step 5: Deploy to Cloud Run

Now let's deploy everything with a single command:

On a Mac/Linux:

```bash
# Plan the deployment (see what will be created)
terraform plan \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

On PC:

```powershell
terraform plan -var ("openai_api_key=" + $Env:OPENAI_API_KEY) -var ("semgrep_app_token=" + $Env:SEMGREP_APP_TOKEN)
```


Review the plan output. You should see:
- ✅ Enable Cloud Run API
- ✅ Enable Container Registry API
- ✅ Enable Cloud Build API
- ✅ Docker image build and push
- ✅ Cloud Run service deployment
- ✅ Public access IAM policy

If everything looks good, apply the changes:

On a Mac/Linux:

```bash
# Deploy everything
terraform apply \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

On a PC:

```powershell
terraform apply -var ("openai_api_key=" + $Env:OPENAI_API_KEY) -var ("semgrep_app_token=" + $Env:SEMGREP_APP_TOKEN)
```


Type `yes` when prompted. This will take 5-10 minutes as it:
1. Enables required Google Cloud APIs
2. Builds your Docker image locally
3. Pushes the image to Google Container Registry
4. Deploys the Cloud Run service
5. Configures public access

**Important**: If you make code changes and redeploy, Terraform may not detect the changes automatically. If your updates don't appear, force a rebuild:

```bash
# Force rebuild of Docker image when code changes (The terraform taint command is deprecated as of Terraform v0.15.2 and later).  Suggest to use
terraform apply -replace="docker_image.app" -replace="docker_registry_image.app" -replace="google_cloud_run_service.app" -var="openai_api_key=$OPENAI_API_KEY" -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

## Step 6: Get Your Application URL

Once deployment completes, Terraform will output your application URL:

```bash
# Get the application URL
terraform output service_url
```

You should see something like:
```
"https://cyber-analyzer-abcdef123-uc.a.run.app"
```

🎉 **Your application is now live!** Visit the URL to test it.

> **Note for Google Workspace users**: If you get an error about organization policies blocking "allUsers", see [Google Workspace Restrictions](#google-workspace-restrictions) at the end of this guide.

---

## Step 7: Verify Deployment

### Test the Application
1. Open the URL from Step 6 in your browser
2. You should see the Cybersecurity Analyzer interface
3. Try uploading a Python file to verify it works end-to-end

### Check Google Cloud Console
In the Cloud Console (https://console.cloud.google.com):
1. Select your project from the dropdown
2. Navigate to **Cloud Run** in the menu
3. You should see your `cyber-analyzer` service
4. Click on it to see metrics, logs, and configuration

### Monitor Logs
```bash
# View application logs
gcloud run services logs read cyber-analyzer \
  --limit=50 \
  --region=$TF_VAR_region

# Stream logs in real-time
gcloud alpha run services logs tail cyber-analyzer \
  --region=$TF_VAR_region
```

---

## Step 8: Clean Up Resources (Important!)

When you're done experimenting with GCP deployment, it's crucial to destroy all resources to avoid ongoing charges. Cloud Run has minimal idle costs, but Container Registry storage and any active traffic will incur charges.

### Destroy All GCP Resources

Run this command from the `terraform/gcp` directory (all on one line):

Mac/Linux:

```bash
terraform destroy -var="openai_api_key=$OPENAI_API_KEY" -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

PC:


```powershell
terraform destroy -var ("openai_api_key=" + $Env:OPENAI_API_KEY) -var ("semgrep_app_token=" + $Env:SEMGREP_APP_TOKEN)
```

Terraform will show you what will be destroyed. Review the list and type `yes` when prompted.

This will remove:
- The Cloud Run service (cyber-analyzer)
- The Docker image from Container Registry
- All associated IAM policies and configurations

### Verify Cleanup in Console

After destruction completes, verify everything is cleaned up:

1. **In Google Cloud Console** (https://console.cloud.google.com):
   - Navigate to **Cloud Run** in the menu
   - Your `cyber-analyzer` service should be gone
   - Navigate to **Container Registry** → **Images**
   - The `cyber-analyzer` image should be removed

2. **Via CLI**:
```bash
# Check Cloud Run services (should be empty or not show cyber-analyzer)
gcloud run services list --region=us-central1

# Check Container Registry images (should not show cyber-analyzer)
gcloud container images list
```

3. **Double-check specific resources**:
```bash
# This should return an error saying the service doesn't exist
gcloud run services describe cyber-analyzer --region=us-central1
```

### Optional: Clean Up Remaining Registry Storage

If any container images remain in the registry:

```bash
# List all images
gcloud container images list

# Delete specific image if it still exists
gcloud container images delete gcr.io/$TF_VAR_project_id/cyber-analyzer --quiet --force-delete-tags
```

**💡 Pro Tip**: Always run `terraform destroy` at the end of each lab session. You can easily redeploy later with `terraform apply` when you need it again. Cloud Run charges are minimal when idle, but it's good practice to clean up learning resources.

---

## Understanding What Was Created

### Cost Breakdown (mostly free tier):
- **Cloud Run**: 2 million requests/month free, then ~$0.40 per million
- **Container Registry**: 0.5GB free storage, then ~$0.05/GB/month
- **Outbound Traffic**: 1GB/month free to North America
- **Total estimated cost**: < $1/month for learning

### Architecture:
```
Internet → Cloud Run Service → Your Docker Image
              ↓
     Google Container Registry
          (image storage)
```

### Resource Configuration:
- **CPU**: 1 vCPU (required for Semgrep processing)
- **Memory**: 2Gi (required for Semgrep rule registry loading)
- **Important**: Lower memory settings will cause Semgrep to fail with SIGKILL

### Scaling:
- **Min instances**: 0 (true scale to zero = $0 when idle)
- **Max instances**: 1 (keeps costs minimal)
- **Auto-scaling**: Based on concurrent requests
- **Cold start**: ~5-10 seconds on first request after idle

---

## Managing Your Deployment

### View Infrastructure State
```bash
# See what's deployed
terraform show

# List all resources
terraform state list
```

### Update the Application
After making code changes:

```bash
# Rebuild and redeploy with a new tag
terraform apply \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="semgrep_app_token=$SEMGREP_APP_TOKEN" \
  -var="docker_image_tag=v2"
```

### View Service Details
```bash
# Get service information
gcloud run services describe cyber-analyzer \
  --region=$TF_VAR_region

# List all revisions
gcloud run revisions list \
  --service=cyber-analyzer \
  --region=$TF_VAR_region
```

### Clean Up (Important for Cost Management!)
When you're done with the lab:

```bash
# Destroy all resources
terraform destroy \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

Type `yes` to confirm. This removes everything and stops all charges.

**Also clean up Container Registry images:**
```bash
# List images
gcloud container images list

# Delete the image (optional, but saves storage costs)
gcloud container images delete gcr.io/$TF_VAR_project_id/cyber-analyzer --quiet
```

---

## Troubleshooting

### "Failed to build Docker image"
- Make sure Docker is running: `docker ps`
- Ensure you're in the correct directory: `terraform/gcp`
- Check Docker has enough disk space: `docker system df`

### "Permission denied" or API errors
```bash
# Re-authenticate
gcloud auth application-default login

# Ensure APIs are enabled
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### "Project not found"
- Verify project ID: `gcloud projects list`
- Ensure TF_VAR_project_id is set correctly
- Check you're in the right project: `gcloud config get-value project`

### "Environment variables not set"
- Re-run the environment variable commands from Step 2
- Check `.env` file exists and has correct format
- On Windows, ensure you're using PowerShell (not Command Prompt)

### Application returns 503 or doesn't load
- Cloud Run has cold starts - wait 10-15 seconds on first access
- Check logs: `gcloud run services logs read cyber-analyzer --limit=50`
- Verify the service is deployed: `gcloud run services list`

### Docker push failures
```bash
# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Retry the deployment
terraform apply -var="openai_api_key=$OPENAI_API_KEY" -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

---

## Comparing Azure vs GCP

### Similarities:
- Both offer serverless container platforms
- Both scale to zero (though Cloud Run is faster)
- Both use similar Terraform patterns
- Both require 2GB RAM for Semgrep

### Key Differences:

| Feature | Azure Container Apps | Google Cloud Run |
|---------|---------------------|------------------|
| Cold Start | ~30 seconds | ~5-10 seconds |
| True Scale to Zero | Sort of (background processes) | Yes (completely stops) |
| Pricing Model | Per vCPU/Memory allocated | Per request + compute time |
| Container Registry | Separate service (ACR) | Integrated (GCR) |
| URL Format | Long subdomain | Shorter, cleaner |
| Free Tier | Limited | Generous (2M requests) |

### Which is Better?
- **For learning**: Cloud Run (better free tier)
- **For production**: Depends on your workload
- **For this course**: Both! Compare and learn

---

## Next Steps

🎉 **Congratulations!** You've successfully deployed to both Azure and GCP!

**What you've learned:**
- Google Cloud Run for serverless containers
- Google Container Registry for image storage
- Cross-platform cloud deployment patterns
- Terraform for multi-cloud infrastructure
- Cost optimization strategies

**Skills gained:**
- Multi-cloud deployment experience
- Infrastructure as Code with Terraform
- Container registry management
- Environment variable handling
- Cloud cost management

Keep both deployments for comparison, but remember to clean up when done to avoid charges!

---

## Google Workspace Restrictions

If you're using a Google Workspace account (custom domain email) instead of a personal Gmail account, you may encounter an error when Terraform tries to make your Cloud Run service publicly accessible:

```
Error: Error applying IAM policy for cloudrun service...
One or more users named in the policy do not belong to a permitted customer, 
perhaps due to an organization policy.
```

This happens because Google Workspace organizations often have domain-restricted sharing policies for security. Here's how to fix it:

### Option 1: Request Organization Policy Exception (Recommended)

If you have admin access to your Google Workspace:

1. **Check your current role**:
```bash
gcloud organizations list
gcloud organizations get-iam-policy YOUR_ORG_ID | grep -A5 "YOUR_EMAIL"
```

2. **Grant yourself Organization Policy Administrator** (if needed):
```bash
gcloud organizations add-iam-policy-binding YOUR_ORG_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/orgpolicy.policyAdmin"
```

3. **Modify the policy in GCP Console**:
   - Go to https://console.cloud.google.com
   - Switch from your organization to your specific project (top-left dropdown)
   - Navigate to **IAM & Admin** → **Organization Policies**
   - Find **"Domain restricted sharing"** (constraints/iam.allowedPolicyMemberDomains)
   - Click **"MANAGE POLICY"**
   - Add a rule with **"Allow All"** for your project
   - Save the changes

4. **Re-run Terraform**:
```bash
terraform apply \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="semgrep_app_token=$SEMGREP_APP_TOKEN"
```

### Option 2: Contact Your Admin

If you don't have admin access:
1. Contact your Google Workspace administrator
2. Request an exception for your cyber-analyzer project
3. They need to allow "allUsers" for Cloud Run services in your project

### Option 3: Use Authenticated Access (Workaround)

If you can't modify the policy, you can still access your deployed service:

```bash
# This creates a local proxy to your Cloud Run service
gcloud run services proxy cyber-analyzer --region=us-central1
```

Then visit http://localhost:8080 in your browser.

### Why This Happens

- **Personal Gmail accounts**: No organization = no restrictions
- **Google Workspace accounts**: Organization policies enforce security by default
- **The fix**: Create a project-specific exception while keeping the organization secure

This is a one-time setup. Once configured, all future deployments to this project will work normally.