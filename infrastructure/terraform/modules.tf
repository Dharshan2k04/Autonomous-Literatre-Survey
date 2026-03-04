# --- Module Orchestration ---

module "networking" {
  source       = "./modules/networking"
  project_name = var.project_name
  vpc_cidr     = var.vpc_cidr
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

module "rds" {
  source             = "./modules/rds"
  project_name       = var.project_name
  environment        = var.environment
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_id  = module.networking.rds_security_group_id
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
}

module "elasticache" {
  source             = "./modules/elasticache"
  project_name       = var.project_name
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_id  = module.networking.redis_security_group_id
}

module "alb" {
  source            = "./modules/alb"
  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  security_group_id = module.networking.alb_security_group_id
}

module "ecs" {
  source       = "./modules/ecs"
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.networking.ecs_security_group_id

  backend_target_group_arn  = module.alb.backend_target_group_arn
  frontend_target_group_arn = module.alb.frontend_target_group_arn

  backend_image  = var.backend_image
  frontend_image = var.frontend_image

  db_host     = module.rds.address
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
  redis_host  = module.elasticache.endpoint

  jwt_secret_key           = var.jwt_secret_key
  openai_api_key           = var.openai_api_key
  anthropic_api_key        = var.anthropic_api_key
  pinecone_api_key         = var.pinecone_api_key
  semantic_scholar_api_key = var.semantic_scholar_api_key
  google_client_id         = var.google_client_id
  google_client_secret     = var.google_client_secret
  github_client_id         = var.github_client_id
  github_client_secret     = var.github_client_secret
}
