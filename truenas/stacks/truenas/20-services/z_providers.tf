// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    truenas = {
      source  = "deevus/truenas"
      version = "0.16.0"
    }
  }
}
variable "truenas_auth_method" {
  default = "ssh"
  type    = string
}
variable "truenas_host" {
  type = string
}
variable "truenas_ssh_host_key_fingerprint" {
  type = string
}
variable "truenas_ssh_port" {
  default = 22
  type    = number
}
variable "truenas_ssh_private_key_file" {
  type = string
}
variable "truenas_ssh_user" {
  default = "terraform"
  type    = string
}
provider "truenas" {
  auth_method = var.truenas_auth_method
  host        = var.truenas_host
  ssh {
    host_key_fingerprint = var.truenas_ssh_host_key_fingerprint
    port                 = var.truenas_ssh_port
    private_key          = file(var.truenas_ssh_private_key_file)
    user                 = var.truenas_ssh_user
  }
}
