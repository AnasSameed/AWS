# Publish the report on Amazon S3

The site is two static files (`site/index.html`, `site/ae_summary.csv`), so S3 static website hosting is enough.
This is the same method as the `s3-static-website` project.

## Option A: AWS console (no tools to install)

1. **S3 → Create bucket.** Name it something globally unique (for example `anas-ae-report-2026`), Region `eu-north-1`.
2. In the bucket's **Permissions** tab, turn **Block public access** off (this report is synthetic and meant to be public). Tick the warning box.
3. **Permissions → Bucket policy**: paste `deploy/bucket-policy.json` and replace `YOUR-BUCKET-NAME` with your bucket name. Save.
4. **Objects → Upload** `site/index.html` and `site/ae_summary.csv`.
5. **Properties → Static website hosting → Edit → Enable.** Index document: `index.html`. Save.
6. Open the **Bucket website endpoint** shown at the bottom of Properties. It is **http** (S3 website endpoints do not support https).

## Option B: AWS CLI (if you have it installed and configured)

```
python python/build_report.py
aws s3 sync site/ s3://YOUR-BUCKET-NAME --delete
```

## Checks

- Page loads but the CSV link gives 403 → the bucket policy is missing or the bucket name in it is wrong.
- 403 on everything → Block public access is still on.
- Old page after an update → hard refresh (Ctrl+F5).

## Clean up (avoid surprises)

Empty the bucket, then delete it. S3 storage for two tiny files costs almost nothing, but do not leave a public bucket you no longer need.

## Never do this with real clinical data

A public bucket is only acceptable for **synthetic** data like this. Real study data needs private buckets, encryption, access logging and your organisation's approved process.
