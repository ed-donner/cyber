terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
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

# Configure Docker provider to use GCR
provider "docker" {
  registry_auth {
    address  = "${var.region}-docker.pkg.dev"
    username = "oauth2accesstoken"
    password = data.google_client_config.default.access_token
  }
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

# Build Docker image
resource "docker_image" "app" {
  name = "${var.region}-docker.pkg.dev/${var.project_id}/${var.service_name}/${var.service_name}:${var.docker_image_tag}"

  build {
    context    = "${path.module}/../.."
    dockerfile = "Dockerfile"
    platform   = "linux/amd64"
    no_cache   = true
  }

  depends_on = [
    google_project_service.cloudbuild,
    google_artifact_registry_repository.app
  ]
}

# Push Docker image to Artifact Registry
resource "docker_registry_image" "app" {
  name = docker_image.app.name
  
  depends_on = [
    google_artifact_registry_repository.app,
    docker_image.app
  ]
}

# Deploy to Cloud Run
resource "google_cloud_run_service" "app" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = docker_image.app.name

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
    docker_registry_image.app
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
