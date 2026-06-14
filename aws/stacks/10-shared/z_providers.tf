// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

terraform {
  required_version = ">= 1.14.9, < 1.16.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.41.0"
    }
  }
}
variable "region" {
  description = "AWS region (from profile location mapping via TF_VAR_region)"
  type        = string
}
provider "aws" {
  region = var.region
  default_tags {
    tags = {
      ManagedBy = "terraform"
      Project   = "ephemeral-cloud-gaming"
    }
  }
}
