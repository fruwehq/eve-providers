// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

variable "profile_name" {
  description = "Instance/profile name used for firewall naming"
  type        = string
}
variable "ssh_allowed_cidr" {
  description = "CIDR allowed to reach SSH"
  type        = string
}
variable "bundle_packages" {
  default     = "ssh"
  description = "Comma-separated package list"
  type        = string
}
data "google_compute_network" "default" {
  name = "default"
}
locals {
  gcp_name    = substr(replace(lower(var.profile_name), "_", "-"), 0, 52)
  package_set = toset(split(",", var.bundle_packages))
}
resource "google_compute_firewall" "ssh" {
  name    = "${local.gcp_name}-ssh"
  network = data.google_compute_network.default.name
  source_ranges = [
    var.ssh_allowed_cidr,
  ]
  target_tags = [
    local.gcp_name,
  ]
  allow {
    ports = [
      "22",
    ]
    protocol = "tcp"
  }
}
resource "google_compute_firewall" "thinlinc" {
  count   = contains(local.package_set, "thinlinc") ? 1 : 0
  name    = "${local.gcp_name}-thinlinc"
  network = data.google_compute_network.default.name
  source_ranges = [
    var.ssh_allowed_cidr,
  ]
  target_tags = [
    local.gcp_name,
  ]
  allow {
    ports = [
      "300",
    ]
    protocol = "tcp"
  }
}
output "firewall_name" {
  value = google_compute_firewall.ssh.name
}
