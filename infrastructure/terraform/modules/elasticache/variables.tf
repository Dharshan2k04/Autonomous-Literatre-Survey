variable "project_name" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }
variable "node_type" {
  type    = string
  default = "cache.t3.micro"
}
variable "num_cache_clusters" {
  type    = number
  default = 1
}
