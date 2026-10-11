# AWS Cloud Projects

Hands-on AWS projects built while learning cloud engineering. Each folder is a self-contained project with its own README, scripts and cleanup steps. All projects are designed to stay within the AWS Free Tier.

| Project | What it shows | Services |
|---|---|---|
| [golden-ami](golden-ami/) | A pre-baked web server image: bake once, launch identical servers in seconds | EC2, AMI, EBS snapshots, IMDSv2, user data |
| [s3-static-website](s3-static-website/) | A website served directly from a bucket, with a public-read bucket policy | S3, bucket policies, static website hosting |

## Learning path
- [x] IAM, EC2, AMI
- [x] S3 static hosting
- [ ] VPC networking
- [ ] Serverless: Lambda, API Gateway, DynamoDB
- [ ] Data on AWS: S3 + Athena

## Notes
- Region used: `eu-north-1` (Stockholm).
- Never commit key files (`*.pem`, `*.ppk`) or access keys. See `.gitignore`.
- Always run each project's cleanup steps so resources do not keep costing money.
