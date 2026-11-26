# Sample insecure Terraform file for demo purposes

# INSECURE: Public S3 bucket
resource "aws_s3_bucket" "public_data" {
  bucket = "my-public-bucket"
  acl    = "public-read"  # S3-001: Public read ACL
}

# INSECURE: Missing encryption
resource "aws_s3_bucket" "sensitive_data" {
  bucket = "my-sensitive-bucket"
  # S3-002: No server-side encryption configuration
}

# INSECURE: Wildcard IAM policy
resource "aws_iam_role_policy" "too_permissive" {
  name = "too-permissive-policy"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["*"]  # IAM-001: Wildcard actions
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "app" {
  name = "app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}
