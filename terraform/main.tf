 terraform {
  backend "s3" {
    encrypt = true
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  default_tags {
    tags = local.default_tags
  }
  region  = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_efs_file_system" "input" {
  creation_token = "${var.prefix}-input"
}

data "aws_efs_file_system" "flpe" {
  creation_token = "${var.prefix}-flpe"
}

data "aws_efs_file_system" "moi" {
  creation_token = "${var.prefix}-moi"
}

data "aws_efs_file_system" "diagnostics" {
  creation_token = "${var.prefix}-diagnostics"
}

data "aws_efs_file_system" "offline" {
  creation_token = "${var.prefix}-offline"
}

data "aws_efs_file_system" "validation" {
  creation_token = "${var.prefix}-validation"
}

data "aws_efs_file_system" "output" {
  creation_token = "${var.prefix}-output"
}

data "aws_efs_file_system" "logs" {
  creation_token = "${var.prefix}-logs"
}

data "aws_iam_role" "job_role" {
  name = "${var.prefix}-batch-job-role"
}

data "aws_iam_role" "exe_role" {
  name = "${var.prefix}-ecs-exe-task-role"
}

locals {
  account_id = sensitive(data.aws_caller_identity.current.account_id)
  default_tags = length(var.default_tags) == 0 ? {
    application : var.app_name,
    environment : lower(var.environment),
    version : var.app_version
  } : var.default_tags
}

module "confluence-init-workflow" {
  source = "./modules/init"
  app_name = var.app_name
  app_version = var.app_version
  aws_region = var.aws_region
  efs_file_system_ids = {
    input = data.aws_efs_file_system.input.file_system_id
    flpe = data.aws_efs_file_system.flpe.file_system_id
    moi = data.aws_efs_file_system.moi.file_system_id
    diagnostics = data.aws_efs_file_system.diagnostics.file_system_id
    offline = data.aws_efs_file_system.offline.file_system_id
    logs = data.aws_efs_file_system.logs.file_system_id
    validation = data.aws_efs_file_system.validation.file_system_id
    output = data.aws_efs_file_system.output.file_system_id
  }
  environment = var.environment
  iam_execution_role_arn = data.aws_iam_role.exe_role.arn
  iam_job_role_arn = data.aws_iam_role.job_role.arn
  prefix = var.prefix
}
