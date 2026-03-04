variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "backend_target_group_arn" { type = string }
variable "frontend_target_group_arn" { type = string }
variable "backend_image" { type = string }
variable "frontend_image" { type = string }

variable "db_host" { type = string }
variable "db_name" { type = string }
variable "db_username" { type = string }
variable "db_password" { type = string }
variable "redis_host" { type = string }
variable "jwt_secret_key" { type = string }
variable "openai_api_key" { type = string }
variable "anthropic_api_key" { type = string }
variable "pinecone_api_key" { type = string }
variable "semantic_scholar_api_key" { type = string }
variable "google_client_id" { type = string }
variable "google_client_secret" { type = string }
variable "github_client_id" { type = string }
variable "github_client_secret" { type = string }

variable "backend_cpu" {
  type    = string
  default = "512"
}
variable "backend_memory" {
  type    = string
  default = "1024"
}
variable "frontend_cpu" {
  type    = string
  default = "256"
}
variable "frontend_memory" {
  type    = string
  default = "512"
}
variable "backend_desired_count" {
  type    = number
  default = 2
}
variable "backend_max_count" {
  type    = number
  default = 4
}
variable "frontend_desired_count" {
  type    = number
  default = 2
}
