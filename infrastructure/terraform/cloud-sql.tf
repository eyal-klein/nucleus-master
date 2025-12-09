# NUCLEUS V1.2 - Cloud SQL (PostgreSQL) Configuration

# Cloud SQL Instance
resource "google_sql_database_instance" "nucleus_db" {
  name             = "nucleus-db-${random_id.suffix.hex}"
  database_version = "POSTGRES_18"
  region           = var.region
  
  settings {
    tier              = var.db_tier
    availability_type = "REGIONAL"  # High availability
    disk_size         = 100  # GB
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"  # 3 AM UTC
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }
    
    ip_configuration {
      ipv4_enabled    = true
      private_network = null  # Public IP for now, can add VPC later
      
      authorized_networks {
        name  = "allow-all"  # TODO: Restrict in production
        value = "0.0.0.0/0"
      }
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = "1024000"  # ~1GB
    }
  }
  
  deletion_protection = true  # Prevent accidental deletion
  
  depends_on = [google_project_service.required_apis]
}

# Main Database
resource "google_sql_database" "nucleus" {
  name     = var.db_name
  instance = google_sql_database_instance.nucleus_db.name
}

# Database User
resource "google_sql_user" "nucleus_user" {
  name     = var.db_user
  instance = google_sql_database_instance.nucleus_db.name
  password = random_password.db_password.result
}

# Generate secure password
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "nucleus-db-password"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Outputs
output "db_instance_name" {
  value = google_sql_database_instance.nucleus_db.name
}

output "db_connection_name" {
  value = google_sql_database_instance.nucleus_db.connection_name
}

output "db_public_ip" {
  value = google_sql_database_instance.nucleus_db.public_ip_address
}
