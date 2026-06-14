// TERRAMATE: GENERATED AUTOMATICALLY DO NOT EDIT

variable "profile_name" {
  default     = "dev-sandbox"
  description = "Profile name used for resource naming and tagging"
  type        = string
}
variable "os_family" {
  default     = "ubuntu"
  description = "OS family: ubuntu or windows"
  type        = string
  validation {
    condition = contains([
      "ubuntu",
      "windows",
    ], var.os_family)
    error_message = "os_family must be ubuntu or windows."
  }
}
variable "instance_type" {
  default     = "t3.large"
  description = "EC2 instance type"
  type        = string
}
variable "disk_gb" {
  default     = 80
  description = "Root volume size in GB"
  type        = number
}
variable "root_volume_type" {
  default     = "gp3"
  description = "Root volume type (e.g., gp3, gp2)"
  type        = string
}
variable "bundle_packages" {
  default     = "ssh"
  description = "Comma-separated list of bundle packages for conditional configuration"
  type        = string
}
variable "use_spot" {
  default     = false
  description = "Use spot instance pricing"
  type        = bool
}
variable "ssh_public_key_file" {
  type = string
}
variable "vm_user_name" {
  default = "ubuntu"
  type    = string
}
variable "availability_zone" {
  description = "AWS availability zone (from profile location mapping via TF_VAR_availability_zone)"
  type        = string
}
data "aws_ami" "ubuntu" {
  count       = var.os_family == "ubuntu" ? 1 : 0
  most_recent = true
  owners = [
    "099720109477",
  ]
  filter {
    name = "name"
    values = [
      "ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*",
    ]
  }
  filter {
    name = "virtualization-type"
    values = [
      "hvm",
    ]
  }
  filter {
    name = "architecture"
    values = [
      "x86_64",
    ]
  }
  filter {
    name = "root-device-type"
    values = [
      "ebs",
    ]
  }
}
data "aws_ami" "windows" {
  count       = var.os_family == "windows" ? 1 : 0
  most_recent = true
  owners = [
    "amazon",
  ]
  filter {
    name = "name"
    values = [
      "Windows_Server-2025-English-Full-Base-*",
    ]
  }
  filter {
    name = "virtualization-type"
    values = [
      "hvm",
    ]
  }
  filter {
    name = "architecture"
    values = [
      "x86_64",
    ]
  }
  filter {
    name = "root-device-type"
    values = [
      "ebs",
    ]
  }
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
  sg_name = "profile-${replace(var.profile_name, "_", "-")}"
}
data "aws_security_group" "default" {
  name   = local.sg_name
  vpc_id = data.aws_vpcs.default.ids[0]
}
data "aws_subnets" "default" {
  filter {
    name = "vpc-id"
    values = [
      data.aws_vpcs.default.ids[0],
    ]
  }
  filter {
    name = "availability-zone"
    values = [
      var.availability_zone,
    ]
  }
  filter {
    name = "default-for-az"
    values = [
      "true",
    ]
  }
}
resource "aws_iam_role" "main" {
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
  name = var.profile_name
}
resource "aws_iam_role_policy_attachment" "ssm" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.main.name
}
resource "aws_iam_instance_profile" "main" {
  name = var.profile_name
  role = aws_iam_role.main.name
}
data "cloudinit_config" "ubuntu" {
  base64_encode = true
  count         = var.os_family == "ubuntu" ? 1 : 0
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
  windows_user_data = templatefile("/Users/chris/src/personal/eve/oses/windows-server-2025/ssh.ps1.tftpl", {
    public_key = trimspace(file(pathexpand(var.ssh_public_key_file)))
  })
}
resource "aws_instance" "main" {
  ami                                  = var.os_family == "ubuntu" ? data.aws_ami.ubuntu[0].id : data.aws_ami.windows[0].id
  iam_instance_profile                 = aws_iam_instance_profile.main.name
  instance_initiated_shutdown_behavior = var.use_spot ? null : "stop"
  instance_type                        = var.instance_type
  subnet_id                            = data.aws_subnets.default.ids[0]
  tags = {
    Project   = "ephemeral-cloud-gaming"
    ManagedBy = "terraform"
    Name      = var.profile_name
  }
  user_data_base64 = var.os_family == "ubuntu" ? data.cloudinit_config.ubuntu[0].rendered : base64encode("<powershell>\n${local.windows_user_data}\n</powershell>")
  vpc_security_group_ids = [
    data.aws_security_group.default.id,
  ]
  root_block_device {
    delete_on_termination = true
    volume_size           = var.disk_gb
    volume_type           = var.root_volume_type
  }
  metadata_options {
    http_tokens = "required"
  }
  dynamic "instance_market_options" {
    for_each = var.use_spot ? [
      1,
      ] : [
    ]
    content {
      market_type = "spot"
      spot_options {
        instance_interruption_behavior = "stop"
        spot_instance_type             = "persistent"
      }
    }
  }
  provisioner "local-exec" {
    command    = self.spot_instance_request_id != "" ? "aws ec2 cancel-spot-instance-requests --region ${substr(self.availability_zone, 0, length(self.availability_zone) - 1)} --spot-instance-request-ids ${self.spot_instance_request_id}" : "true"
    on_failure = continue
    when       = destroy
  }
}
output "instance_id" {
  value = aws_instance.main.id
}
output "public_ip" {
  value = aws_instance.main.public_ip
}
