# S3 Security Review Checklist

Use this as a learning checklist, not as an automatic production approval.

## Access
- [ ] Block Public Access is enabled at account and bucket level where appropriate.
- [ ] Bucket policy has been reviewed for unintended public or cross-account access.
- [ ] IAM permissions follow least privilege.
- [ ] Workloads use IAM roles / temporary credentials where possible.
- [ ] Object Ownership is `Bucket owner enforced` unless ACLs are specifically required.
- [ ] ACLs are disabled for the normal policy-based access model.

## Network and browser access
- [ ] HTTPS/TLS is required by policy.
- [ ] CORS lists only required origins, methods, and headers.
- [ ] Team understands CORS does not grant authorization.
- [ ] VPC endpoint restrictions are considered for private workloads.

## Data protection
- [ ] Default encryption is understood and verified.
- [ ] SSE-KMS is used where key-control or audit requirements justify it.
- [ ] KMS key policies and grants are reviewed.
- [ ] Versioning is enabled for important data.
- [ ] Object Lock is considered for immutable retention requirements.
- [ ] Lifecycle rules account for noncurrent versions and incomplete multipart uploads.
- [ ] Replication and restore procedures are tested where required.

## Monitoring and operations
- [ ] CloudTrail management events are available.
- [ ] S3 data events are enabled where object-level audit is required.
- [ ] Access logging / monitoring destination is protected.
- [ ] Alerts and ownership for security findings are defined.
- [ ] Recovery from accidental deletion and compromised credentials is tested.

## Before committing to GitHub
- [ ] No AWS access keys, secret keys, session tokens, passwords, or private data.
- [ ] No real presigned URLs or sensitive bucket names/account IDs.
- [ ] All placeholders are clearly marked.
