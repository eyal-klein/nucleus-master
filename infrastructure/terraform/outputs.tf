# NUCLEUS V1.2 - Terraform Outputs

# Project Info
output "nucleus_project_info" {
  description = "NUCLEUS project information"
  value = {
    project_id = var.project_id
    region     = var.region
    environment = var.environment
  }
}

# Database Connection String (for services)
output "database_connection_string" {
  description = "PostgreSQL connection string"
  value       = "postgresql://${var.db_user}:${random_password.db_password.result}@${google_sql_database_instance.nucleus_db.public_ip_address}:5432/${var.db_name}"
  sensitive   = true
}

# Database Connection Name (for Cloud SQL Proxy)
output "database_connection_name_for_cloud_run" {
  description = "Cloud SQL connection name for Cloud Run"
  value       = google_sql_database_instance.nucleus_db.connection_name
}

# All Infrastructure Summary
output "infrastructure_summary" {
  description = "Summary of all deployed infrastructure"
  value = {
    database = {
      instance_name    = google_sql_database_instance.nucleus_db.name
      connection_name  = google_sql_database_instance.nucleus_db.connection_name
      database_name    = var.db_name
      user             = var.db_user
    }
    storage = {
      main_bucket = google_storage_bucket.nucleus_storage.name
    }
    pubsub = {
      topics_count        = length(google_pubsub_topic.topics)
      subscriptions_count = 7
    }
  }
}
