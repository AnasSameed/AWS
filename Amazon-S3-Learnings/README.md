# Amazon S3 Security & Core Concepts

Beginner-friendly notes and practical examples for learning Amazon S3 security.

## Contents
- `Amazon-S3-Security-Study-Guide.pdf` — study notes covering S3, CORS, encryption, IAM, bucket policies, Block Public Access, versioning, Object Lock, replication, lifecycle, presigned URLs, access points, VPC endpoints, and monitoring.
- `examples/` — starter JSON examples.
- `docs/security-checklist.md` — review checklist.
- `docs/interview-questions.md` — quick revision questions.

## Suggested learning path
1. Understand buckets, objects, keys, prefixes, and Regions.
2. Learn IAM identity policies and bucket policies.
3. Configure Block Public Access and Object Ownership.
4. Understand CORS and test browser requests.
5. Compare SSE-S3 and SSE-KMS; enforce HTTPS.
6. Enable versioning and learn Object Lock.
7. Explore lifecycle rules and replication.
8. Configure CloudTrail data events and review access.

## Important safety notes
- These examples are templates, not production-ready policies.
- Replace every placeholder such as `YOUR_BUCKET_NAME`, `YOUR_ACCOUNT_ID`, and `https://app.example.com`.
- Never commit AWS access keys, secret keys, session tokens, passwords, private customer files, or real presigned URLs.
- Do not disable Block Public Access simply to make an application work. Diagnose the required access path first.
- CORS does not grant S3 permissions. IAM and bucket policies still control authorization.
- Test in a dedicated sandbox bucket before using policies or lifecycle rules on important data.

## Validate JSON
Use a JSON validator or:
```bash
python -m json.tool examples/cors-configuration.json
```

## Official AWS references
- [S3 security best practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)
- [S3 CORS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html)
- [S3 encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingEncryption.html)
- [S3 access management](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-management.html)

_Last reviewed: 17 November 2026._
