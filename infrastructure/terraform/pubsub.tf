# NUCLEUS V1.2 - Google Cloud Pub/Sub Configuration

# Create Topics
resource "google_pubsub_topic" "topics" {
  for_each = toset(var.pubsub_topics)
  
  name = each.key
  
  message_retention_duration = "604800s"  # 7 days
  
  depends_on = [google_project_service.required_apis]
}

# Create Subscriptions for Services
resource "google_pubsub_subscription" "orchestrator_tasks" {
  name  = "nucleus-orchestrator-tasks-sub"
  topic = google_pubsub_topic.topics["nucleus-tasks"].name
  
  ack_deadline_seconds = 600  # 10 minutes
  
  message_retention_duration = "604800s"  # 7 days
  retain_acked_messages      = false
  
  expiration_policy {
    ttl = ""  # Never expire
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "results_analysis_results" {
  name  = "nucleus-results-analysis-sub"
  topic = google_pubsub_topic.topics["nucleus-results"].name
  
  ack_deadline_seconds = 600
  
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  
  expiration_policy {
    ttl = ""
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "agent_evolution_events" {
  name  = "nucleus-agent-evolution-sub"
  topic = google_pubsub_topic.topics["nucleus-events"].name
  
  ack_deadline_seconds = 600
  
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  
  # Filter for agent-related events
  filter = "attributes.event_type = \"agent_analysis_complete\""
  
  expiration_policy {
    ttl = ""
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Create Subscriptions for Jobs
resource "google_pubsub_subscription" "dna_engine_job" {
  name  = "nucleus-dna-engine-job-sub"
  topic = google_pubsub_topic.topics["nucleus-events"].name
  
  ack_deadline_seconds = 600
  
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  
  filter = "attributes.event_type = \"trigger_dna_analysis\""
  
  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_subscription" "first_interpretation_job" {
  name  = "nucleus-first-interpretation-job-sub"
  topic = google_pubsub_topic.topics["nucleus-dna-updated"].name
  
  ack_deadline_seconds = 600
  
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  
  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_subscription" "qa_job" {
  name  = "nucleus-qa-job-sub"
  topic = google_pubsub_topic.topics["nucleus-agent-created"].name
  
  ack_deadline_seconds = 600
  
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  
  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_subscription" "activation_job" {
  name  = "nucleus-activation-job-sub"
  topic = google_pubsub_topic.topics["nucleus-agent-validated"].name
  
  ack_deadline_seconds = 600
  
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  
  expiration_policy {
    ttl = ""
  }
}

# Outputs
output "pubsub_topics" {
  value = [for topic in google_pubsub_topic.topics : topic.name]
}

output "pubsub_subscriptions" {
  value = {
    orchestrator_tasks         = google_pubsub_subscription.orchestrator_tasks.name
    results_analysis_results   = google_pubsub_subscription.results_analysis_results.name
    agent_evolution_events     = google_pubsub_subscription.agent_evolution_events.name
    dna_engine_job            = google_pubsub_subscription.dna_engine_job.name
    first_interpretation_job  = google_pubsub_subscription.first_interpretation_job.name
    qa_job                    = google_pubsub_subscription.qa_job.name
    activation_job            = google_pubsub_subscription.activation_job.name
  }
}
