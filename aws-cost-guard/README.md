# aws-cost-guard

A small **read-only** scanner that lists the most common ways an AWS learning account quietly bleeds money, with a rough monthly cost for each so you can fix the biggest first.

| Finding | Why it costs money | Suggested action |
|---|---|---|
| Unattached EBS volumes | Billed per GiB even when nothing uses them | Snapshot if needed, delete |
| Idle Elastic IPs | Billed per hour when not associated | Release |
| Old EBS snapshots (default > 90 days) | Billed per GiB-month | Review retention, delete (AMI-backing ones: deregister the AMI first) |
| Running instances with no `Owner` tag (default > 30 days) | Nobody knows who should stop them | Tag or stop |

## Use

```bash
pip install -r requirements.txt
python cost_guard.py --region ap-south-1                 # uses your default AWS credentials
python cost_guard.py --region us-east-1 --profile learning --json report.json
pytest -q                                                # offline tests, no AWS account needed
```

Exit code is 1 when something was found (handy in a scheduled job) and 0 when clean.

## Safety

- Only four EC2 `Describe*` calls are made. The tool **never stops, deletes or releases anything**; you act on the report yourself.
- `iam-policy.json` is the matching least-privilege policy: attach it to a dedicated IAM user or role instead of running this with admin credentials. A test checks that the policy contains only `ec2:Describe*` actions.

## How it is tested

The EC2 client is injected, so the tests use a fake one: they cover pagination across several pages, boundary ages (exactly 90 days is not "older than 90"), attached vs unattached volumes, associated vs idle IPs, tag handling, report sorting, and that **only Describe calls** are made.

## Status and limits

- **Not yet run against a real AWS account** from the build environment (no credentials there). The API calls and response fields follow the documented boto3 EC2 API; if a field differs in your account, please open an issue.
- Cost figures are rough list-price constants (`PRICES` in `cost_guard.py`), not your bill. Check Cost Explorer for real numbers.
- One region per run, EC2 resources only. Not covered: NAT gateways, load balancers, RDS, S3 lifecycle, unused Lambda.
- Snapshots in use by an AMI are flagged by their description text only.

## Ideas for next steps

- Loop over all regions; add NAT gateways and idle load balancers
- Run as a weekly Lambda + SNS email using the same policy
