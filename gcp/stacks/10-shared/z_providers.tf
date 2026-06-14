// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

terraform {
  required_version = ">= 1.14.9, < 1.16.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.12.0"
    }
  }
}
variable "project_id" {
  description = "GCP project id (from GOOGLE_CLOUD_PROJECT/GOOGLE_PROJECT)"
  type        = string
}
variable "region" {
  description = "GCP region (from catalog location mapping)"
  type        = string
}
variable "zone" {
  description = "GCP zone (from catalog location mapping)"
  type        = string
}
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
