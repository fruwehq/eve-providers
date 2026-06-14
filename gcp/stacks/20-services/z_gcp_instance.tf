// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

variable "profile_name" {
  default     = "dev-sandbox"
  description = "Instance/profile name used for resource naming"
  type        = string
}
variable "os_family" {
  default     = "ubuntu"
  description = "OS family"
  type        = string
  validation {
    condition = contains([
      "ubuntu",
    ], var.os_family)
    error_message = "gcp currently supports ubuntu instances."
  }
}
variable "machine_type" {
  default     = "e2-small"
  description = "GCP machine type"
  type        = string
}
variable "disk_gb" {
  default     = 20
  description = "Boot disk size in GB"
  type        = number
}
variable "disk_type" {
  default     = "pd-balanced"
  description = "Boot disk type"
  type        = string
}
variable "image_project" {
  description = "GCP image project"
  type        = string
}
variable "image_family" {
  description = "GCP image family"
  type        = string
}
variable "bundle_packages" {
  default     = "ssh"
  description = "Comma-separated package list"
  type        = string
}
variable "ssh_public_key_file" {
  type = string
}
variable "vm_user_name" {
  default = "ubuntu"
  type    = string
}
data "google_compute_image" "ubuntu" {
  family  = var.image_family
  project = var.image_project
}
data "cloudinit_config" "ubuntu" {
  base64_encode = false
  gzip          = false
  part {
    content = yamlencode({
      hostname         = replace(var.profile_name, "_", "-")
      manage_etc_hosts = true
      users = [
        {
          name        = var.vm_user_name
          sudo        = "ALL=(ALL) NOPASSWD:ALL"
          shell       = "/bin/bash"
          lock_passwd = false
          ssh_authorized_keys = [
            trimspace(file(pathexpand(var.ssh_public_key_file))),
          ]
        },
      ]
      package_update  = true
      package_upgrade = true
      packages = [
        "curl",
        "git",
        "jq",
      ]
    })
    content_type = "text/cloud-config"
    filename     = "cloud-config.yaml"
  }
}
locals {
  gcp_name       = substr(replace(lower(var.profile_name), "_", "-"), 0, 52)
  ssh_public_key = trimspace(file(pathexpand(var.ssh_public_key_file)))
}
resource "google_compute_instance" "main" {
  labels = {
    managed_by = "terraform"
    project    = "ephemeral-cloud-gaming"
  }
  machine_type = var.machine_type
  metadata = {
    ssh-keys  = "${var.vm_user_name}:${local.ssh_public_key}"
    user-data = data.cloudinit_config.ubuntu.rendered
  }
  name = local.gcp_name
  tags = [
    local.gcp_name,
  ]
  boot_disk {
    initialize_params {
      image = data.google_compute_image.ubuntu.self_link
      size  = var.disk_gb
      type  = var.disk_type
    }
  }
  network_interface {
    network = "default"
    access_config {
    }
  }
  scheduling {
    automatic_restart   = false
    on_host_maintenance = "MIGRATE"
  }
}
output "instance_id" {
  value = google_compute_instance.main.id
}
output "instance_name" {
  value = google_compute_instance.main.name
}
output "public_ip" {
  value = google_compute_instance.main.network_interface[0].access_config[0].nat_ip
}
