# NUCLEUS V1.2 - Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "thrive-system1"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# Database
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-custom-2-7680"  # 2 vCPU, 7.68 GB RAM
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "nucleus"
}

variable "db_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "nucleus"
}

# Pub/Sub
variable "pubsub_topics" {
  description = "List of Pub/Sub topics to create"
  type        = list(string)
  default = [
    "nucleus-tasks",
    "nucleus-results",
    "nucleus-events",
    "nucleus-dna-updated",
    "nucleus-agent-created",
    "nucleus-agent-validated",
  ]
}

# Storage
variable "gcs_bucket_name" {
  description = "GCS bucket name for file storage"
  type        = string
  default     = "nucleus-storage"
}
