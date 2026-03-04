# -----------------------------------------------------------------------
# ElastiCache Redis
# -----------------------------------------------------------------------
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.common_tags
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.name_prefix}-redis"
  description          = "Redis for session management and caching"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_clusters   = 2
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  automatic_failover_enabled = true
  multi_az_enabled           = true

  maintenance_window       = "sun:05:00-sun:06:00"
  snapshot_retention_limit = 3
  snapshot_window          = "04:00-05:00"

  apply_immediately = true
  tags              = merge(local.common_tags, { Name = "${local.name_prefix}-redis" })
}
