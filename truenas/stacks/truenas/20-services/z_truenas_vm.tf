// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

variable "profile_name" {
  type = string
}
variable "os_id" {
  type = string
}
variable "location_name" {
  type = string
}
variable "vm_memory_mb" {
  default = 8192
  type    = number
}
variable "vm_cpu_cores" {
  default = 4
  type    = number
}
variable "vm_vcpus" {
  default = 1
  type    = number
}
variable "vm_cpu_mode" {
  default = "CUSTOM"
  type    = string
}
variable "vm_autostart" {
  default = true
  type    = bool
}
variable "vm_state" {
  default = "RUNNING"
  type    = string
}
variable "vm_nic_attach" {
  default = "br0"
  type    = string
}
variable "vm_disk_gb" {
  default = 30
  type    = number
}
variable "vm_base_dir" {
  default = ""
  type    = string
}
variable "vm_pool" {
  default = "main"
  type    = string
}
variable "vm_zvol_prefix" {
  default = "vms"
  type    = string
}
variable "ssh_public_key_file" {
  type = string
}
variable "vm_user_name" {
  default = "ubuntu"
  type    = string
}
variable "provision_user_name" {
  default = "eve-provision"
  type    = string
}
variable "cloud_image_url" {
  default = ""
  type    = string
}
locals {
  base_dir    = var.vm_base_dir
  images_dir  = "${local.base_dir}/images"
  iso_path    = "${local.base_dir}/iso/${local.vm_name}-${var.os_id}-cidata.iso"
  vm_name     = join("", regexall("[a-zA-Z0-9]+", var.profile_name))
  zvol_device = "/dev/zvol/${var.vm_pool}/${local.zvol_path}"
  zvol_path   = "${var.vm_zvol_prefix}/${local.vm_name}"
}
resource "null_resource" "verify_parent_dataset" {
  triggers = {
    base_dir = local.base_dir
  }
  provisioner "local-exec" {
    command = "\"$(git rev-parse --show-toplevel)/plugins/providers/truenas/commands/dataset-verify\" '${local.base_dir}'"
  }
}
resource "truenas_zvol" "this" {
  depends_on = [
    null_resource.verify_parent_dataset,
  ]
  path    = local.zvol_path
  pool    = var.vm_pool
  sparse  = true
  volsize = "${var.vm_disk_gb * 1024}M"
}
resource "null_resource" "write_cloud_image" {
  count = var.cloud_image_url != "" ? 1 : 0
  depends_on = [
    truenas_zvol.this,
  ]
  triggers = {
    zvol_id         = truenas_zvol.this.id
    cloud_image_url = var.cloud_image_url
    disk_gb         = var.vm_disk_gb
  }
  provisioner "local-exec" {
    command = join(" ", [
      "\"$(git rev-parse --show-toplevel)/plugins/providers/truenas/commands/vm-disk-prepare\"",
      "'${var.truenas_host}'",
      "'${local.images_dir}'",
      "'${local.zvol_device}'",
      "'${local.vm_name}'",
      "'${var.cloud_image_url}'",
      "'${var.vm_disk_gb}'",
    ])
  }
}
resource "null_resource" "cloudinit_iso" {
  triggers = {
    vm_name             = local.vm_name
    os_id               = var.os_id
    truenas_host        = var.truenas_host
    iso_path            = local.iso_path
    provision_user_name = var.provision_user_name
    vm_user_name        = var.vm_user_name
    ssh_public_key      = trimspace(file(var.ssh_public_key_file))
  }
  provisioner "local-exec" {
    command = "\"$(git rev-parse --show-toplevel)/plugins/providers/truenas/commands/cloudinit-upload\" '${local.vm_name}' '${var.ssh_public_key_file}' '${var.truenas_host}' '${local.iso_path}' '${var.provision_user_name}' '${var.vm_user_name}'"
  }
  provisioner "local-exec" {
    command = "\"$(git rev-parse --show-toplevel)/plugins/providers/truenas/commands/cloudinit-delete\" '${self.triggers.truenas_host}' '${self.triggers.iso_path}'"
    when    = destroy
  }
}
resource "truenas_vm" "this" {
  autostart = var.vm_autostart
  cores     = var.vm_cpu_cores
  cpu_mode  = var.vm_cpu_mode
  depends_on = [
    null_resource.write_cloud_image,
    null_resource.cloudinit_iso,
  ]
  description = "Profile=${var.profile_name}; OS=${var.os_id}; Location=${var.location_name}"
  memory      = var.vm_memory_mb
  name        = local.vm_name
  state       = var.vm_state
  vcpus       = var.vm_vcpus
  nic {
    nic_attach = var.vm_nic_attach
    type       = "VIRTIO"
  }
  disk {
    path = local.zvol_device
    type = "VIRTIO"
  }
  cdrom {
    path = local.iso_path
  }
}
output "truenas_vm_id" {
  value = truenas_vm.this.id
}
output "truenas_vm_name" {
  value = truenas_vm.this.name
}
output "truenas_vm_mac" {
  value = try(truenas_vm.this.nic[0].mac, "")
}
