variable "region_id" {
  default = "us-east-1"
}

variable "prefix" {
  default = "tech-challanger-4"
}

variable "account" {
  default = 593793061865
}

# Prefix configuration and project common tags
locals {
  prefix = "${var.prefix}-${terraform.workspace}"
  common_tags = {
    Project      = "tech-challanger-2"
    ManagedBy    = "Terraform"
    Department   = "TI",
    Provider     = "students",
    Owner        = "Data Engineering"
    BusinessUnit = "Data"
    Billing      = "Infrastructure"
    Environment  = terraform.workspace
    UserEmail    = "sebastiao553@gmail.com"
  }
}

variable "bucket_names" {
  description = "Create S3 buckets with these names"
  type        = list(string)
  default = [
    "raw-zone",
    "delivery-zone"
  ]
}

variable "database_names" {
  description = "Create databases with these names"
  type        = list(string)
  default = [
    #landing-zone
    "dl-raw-zone",
    "dl-delivery-zone"
  ]
}
