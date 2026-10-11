# S3 Static Website

A small website hosted directly from an Amazon S3 bucket: no server, no operating system to patch, and a cost of well under a dollar a month.

## What this shows
- Creating an S3 bucket and uploading objects
- Enabling **static website hosting** with index and error documents
- Writing a **bucket policy** that allows public read access to objects only
- Understanding **Block Public Access**, and why it must be relaxed for a public website

## Layout
```
website/
  index.html            home page
  error.html            shown for missing pages (404)
policy/
  bucket-policy.json    public-read policy (replace YOUR-BUCKET-NAME)
```

## Steps (AWS Console)
1. **S3 -> Create bucket.** Name it something globally unique, region `eu-north-1`.
2. Under *Block Public Access*, untick **Block all public access** and tick the acknowledgement. (Website only; never do this for private data.)
3. **Upload** `website/index.html` and `website/error.html`.
4. **Properties -> Static website hosting -> Edit -> Enable.** Index document `index.html`, error document `error.html`. Save, then note the *Bucket website endpoint*.
5. **Permissions -> Bucket policy -> Edit.** Paste `policy/bucket-policy.json` with your bucket name in place of `YOUR-BUCKET-NAME`.
6. Open the website endpoint in a browser. (It is `http://`, not `https://`.)

## Design notes
- The policy grants only `s3:GetObject`, so visitors can read files but cannot list, upload or delete.
- The S3 website endpoint serves HTTP only. For HTTPS and a custom domain, put **CloudFront** in front of a private bucket (planned).

## Cost
A few small files stay inside the AWS Free Tier. Delete the bucket when finished: empty it first, then delete it.

## Roadmap
- [ ] Add a screenshot of the live site to `docs/`
- [ ] Enable versioning and a lifecycle rule
- [ ] Put CloudFront in front with Origin Access Control and HTTPS
