variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "autlit-survey"
}

variable "environment" {
  description = "Deployment environment (dev / staging / prod)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# -----------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# -----------------------------------------------------------------------
# ECR / Container
# -----------------------------------------------------------------------
variable "backend_image_tag" {
  description = "Docker image tag for the backend service"
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Docker image tag for the frontend service"
  type        = string
  default     = "latest"
}

# -----------------------------------------------------------------------
# ECS
# -----------------------------------------------------------------------
variable "backend_cpu" {
  description = "Backend task CPU units (1 vCPU = 1024)"
  type        = number
  default     = 1024
}

variable "backend_memory" {
  description = "Backend task memory in MiB"
  type        = number
  default     = 2048
}

variable "frontend_cpu" {
  description = "Frontend task CPU units"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Frontend task memory in MiB"
  type        = number
  default     = 512
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 4
}

variable "scale_up_cpu_threshold" {
  description = "CPU % that triggers scale-up"
  type        = number
  default     = 70
}

variable "scale_down_cpu_threshold" {
  description = "CPU % that triggers scale-down"
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------
# RDS
# -----------------------------------------------------------------------
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "literature_survey"
}

variable "db_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

# -----------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# -----------------------------------------------------------------------
# Secrets (stored in SSM / Secrets Manager, referenced at runtime)
# -----------------------------------------------------------------------
variable "openai_api_key" {
  description = "OpenAI API key (stored in SSM Parameter Store)"
  type        = string
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key (stored in SSM Parameter Store)"
  type        = string
  sensitive   = true
}
