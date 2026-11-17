# S3 Security — Quick Interview Questions

1. What is an S3 bucket and what is an object?
2. What is the difference between a bucket name, object key, and prefix?
3. What problem does CORS solve? Does CORS authorize access?
4. Compare SSE-S3, SSE-KMS, DSSE-KMS, and SSE-C.
5. What is the difference between encryption at rest and encryption in transit?
6. What are the four S3 Block Public Access settings?
7. Compare an IAM identity policy with an S3 bucket policy.
8. What is S3 Object Ownership and why is Bucket owner enforced commonly recommended?
9. How does S3 Versioning help with recovery? What does it not protect against by itself?
10. Compare Object Lock Governance mode and Compliance mode.
11. What is a presigned URL and whose permissions does it use?
12. Compare Same-Region Replication and Cross-Region Replication.
13. What is the purpose of an S3 lifecycle rule?
14. What is the difference between CloudTrail management events and S3 data events?
15. When would you use an S3 VPC endpoint or Access Point?

## Short answer key
1. Bucket is a container; object is stored data plus metadata.
2. Key identifies an object; prefix is a grouping pattern within keys.
3. CORS controls browser cross-origin behavior; it is not authorization.
4. S3-managed keys; KMS keys; dual-layer KMS encryption; customer-provided key.
5. Stored data versus data moving over a network.
6. BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy, RestrictPublicBuckets.
7. Identity-attached permissions versus resource-attached bucket permissions.
8. Bucket owner owns objects and ACLs are disabled.
9. Retains versions; lifecycle and access controls are still needed.
10. Governance can be bypassed by specially authorized principals; Compliance cannot be bypassed during retention.
11. Temporary signed request for an object/action, based on signer permissions.
12. Replication within the same Region versus across Regions.
13. Automates transitions and expiration.
14. Management events track control-plane actions; data events track object-level operations.
15. Private VPC-to-S3 connectivity; separately scoped access endpoint/policy.
