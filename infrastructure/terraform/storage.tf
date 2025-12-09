# NUCLEUS V1.2 - Google Cloud Storage Configuration

# Main storage bucket
resource "google_storage_bucket" "nucleus_storage" {
  name          = "${var.gcs_bucket_name}-${random_id.suffix.hex}"
  location      = var.region
  force_destroy = false  # Prevent accidental deletion
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90  # days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 365  # days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Terraform state bucket
resource "google_storage_bucket" "terraform_state" {
  name          = "nucleus-terraform-state"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  depends_on = [google_project_service.required_apis]
}

# Outputs
output "storage_bucket_name" {
  value = google_storage_bucket.nucleus_storage.name
}

output "storage_bucket_url" {
  value = google_storage_bucket.nucleus_storage.url
}
