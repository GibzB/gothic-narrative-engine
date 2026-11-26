# Sample secure Terraform file for demo purposes

# SECURE: Private S3 bucket with encryption
resource "aws_s3_bucket" "secure_data" {
  bucket = "my-secure-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure_data_encryption" {
  bucket = aws_s3_bucket.secure_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "secure_data_block" {
  bucket = aws_s3_bucket.secure_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# SECURE: Scoped IAM policy
resource "aws_iam_role_policy" "scoped_policy" {
  name = "scoped-policy"
  role = aws_iam_role.secure_app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.secure_data.arn,
          "${aws_s3_bucket.secure_data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role" "secure_app" {
  name = "secure-app-role"
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
