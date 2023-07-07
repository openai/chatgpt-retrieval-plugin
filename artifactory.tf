resource "google_project_service" "artifact_registry_api" {
  service = "artifactregistry.googleapis.com"
}

resource "google_artifact_registry_repository" "chatgpt_repo" {
  location      = var.region
  repository_id = "chatgpt-retrieval-plugin"
  description   = "Docker image for chatgpt plugin api"
  format        = "DOCKER"
}