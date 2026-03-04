variable "project_name" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }
variable "db_name" { type = string }
variable "db_username" { type = string }
variable "db_password" { type = string }
variable "environment" { type = string }
variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}
variable "multi_az" {
  type    = bool
  default = false
}
