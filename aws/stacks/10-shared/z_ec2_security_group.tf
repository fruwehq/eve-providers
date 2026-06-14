// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

variable "profile_name" {
  default     = "dev-sandbox"
  description = "Profile name used for security group naming"
  type        = string
}
variable "os_family" {
  default     = "ubuntu"
  description = "OS family: ubuntu or windows"
  type        = string
}
variable "bundle_packages" {
  default     = "ssh"
  description = "Comma-separated list of bundle packages for rule selection"
  type        = string
}
data "aws_vpcs" "default" {
  filter {
    name = "isDefault"
    values = [
      "true",
    ]
  }
}
locals {
  package_set = toset(split(",", var.bundle_packages))
  sg_name     = "profile-${replace(var.profile_name, "_", "-")}"
}
resource "aws_security_group" "default" {
  description = "Security group for profile: ${var.profile_name}"
  name        = local.sg_name
  vpc_id      = data.aws_vpcs.default.ids[0]
  ingress {
    cidr_blocks = local.allowed_cidrs
    description = "SSH"
    from_port   = 22
    protocol    = "tcp"
    to_port     = 22
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight TCP"
      from_port   = 47984
      protocol    = "tcp"
      to_port     = 47984
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight TCP"
      from_port   = 47989
      protocol    = "tcp"
      to_port     = 47989
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Sunshine Web UI"
      from_port   = 47990
      protocol    = "tcp"
      to_port     = 47990
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight UDP"
      from_port   = 47998
      protocol    = "udp"
      to_port     = 47998
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight UDP"
      from_port   = 47999
      protocol    = "udp"
      to_port     = 47999
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight UDP"
      from_port   = 48000
      protocol    = "udp"
      to_port     = 48000
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight UDP"
      from_port   = 48002
      protocol    = "udp"
      to_port     = 48002
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight TCP"
      from_port   = 48010
      protocol    = "tcp"
      to_port     = 48010
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "sunshine") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Moonlight UDP"
      from_port   = 48010
      protocol    = "udp"
      to_port     = 48010
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "steam") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Steam UDP"
      from_port   = 27031
      protocol    = "udp"
      to_port     = 27031
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "steam") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Steam TCP"
      from_port   = 27036
      protocol    = "tcp"
      to_port     = 27036
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "steam") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "Steam UDP"
      from_port   = 27037
      protocol    = "udp"
      to_port     = 27037
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "rustdesk") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "RustDesk TCP"
      from_port   = 21116
      protocol    = "tcp"
      to_port     = 21116
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "rustdesk") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "RustDesk UDP"
      from_port   = 21116
      protocol    = "udp"
      to_port     = 21116
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "rustdesk") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "RustDesk TCP"
      from_port   = 21117
      protocol    = "tcp"
      to_port     = 21117
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "rustdesk") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "RustDesk TCP"
      from_port   = 21118
      protocol    = "tcp"
      to_port     = 21118
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "rustdesk") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "RustDesk TCP"
      from_port   = 21119
      protocol    = "tcp"
      to_port     = 21119
    }
  }
  dynamic "ingress" {
    for_each = contains(local.package_set, "thinlinc") ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "ThinLinc Web Access"
      from_port   = 300
      protocol    = "tcp"
      to_port     = 300
    }
  }
  dynamic "ingress" {
    for_each = var.os_family == "windows" ? [
      1,
      ] : [
    ]
    content {
      cidr_blocks = local.allowed_cidrs
      description = "RDP"
      from_port   = 3389
      protocol    = "tcp"
      to_port     = 3389
    }
  }
  egress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    description = "Allow all egress"
    from_port   = 0
    ipv6_cidr_blocks = [
      "::/0",
    ]
    protocol = "-1"
    to_port  = 0
  }
}
