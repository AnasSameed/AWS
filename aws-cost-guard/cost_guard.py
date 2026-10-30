"""
cost_guard: a READ-ONLY scanner for common AWS cost leaks in one region.

    python cost_guard.py --region ap-south-1
    python cost_guard.py --region us-east-1 --snapshot-age-days 60 --json report.json

What it looks for
  * unattached EBS volumes (state "available"): billed for size, used by nothing
  * Elastic IPs not associated with anything
  * EBS snapshots you own that are older than N days (default 90)
  * running EC2 instances with no Owner tag, and running for more than N days (default 30)

Safety: only EC2 Describe* calls are made. Nothing is stopped, deleted or released; the tool
only reports. The IAM policy in iam-policy.json grants those four Describe actions and nothing else.

Costs are ROUGH monthly estimates from the constants in PRICES (approximate on-demand list
prices for a common region). They are there to rank findings, not to replace Cost Explorer.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# approximate USD per GB-month / per month; check current pricing for your region
PRICES = {
    "ebs_gb_month": {"gp3": 0.08, "gp2": 0.10, "io1": 0.125, "io2": 0.125,
                     "st1": 0.045, "sc1": 0.015, "standard": 0.05, "default": 0.10},
    "snapshot_gb_month": 0.05,
    "elastic_ip_month": 3.65,          # $0.005 per hour
}


@dataclass
class Finding:
    kind: str                # unattached_volume | idle_elastic_ip | old_snapshot | untagged_running_instance
    resource_id: str
    detail: str
    est_monthly_usd: float
    suggestion: str


# --------------------------------------------------------------------------- helpers
def _tags(resource: Dict[str, Any]) -> Dict[str, str]:
    return {t["Key"]: t.get("Value", "") for t in resource.get("Tags", [])}


def _paginate(client, operation: str, result_key: str, **kwargs):
    for page in client.get_paginator(operation).paginate(**kwargs):
        for item in page.get(result_key, []):
            yield item


def _age_days(when: datetime, now: datetime) -> int:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (now - when).days


# --------------------------------------------------------------------------- scanners
def find_unattached_volumes(ec2) -> List[Finding]:
    out = []
    for v in _paginate(ec2, "describe_volumes", "Volumes",
                       Filters=[{"Name": "status", "Values": ["available"]}]):
        if v.get("State") != "available":          # defensive: a fake or odd response
            continue
        rate = PRICES["ebs_gb_month"].get(v.get("VolumeType"), PRICES["ebs_gb_month"]["default"])
        name = _tags(v).get("Name", "")
        out.append(Finding("unattached_volume", v["VolumeId"],
                           f"{v['Size']} GiB {v.get('VolumeType', '?')}" + (f", Name={name}" if name else ""),
                           round(v["Size"] * rate, 2),
                           "Snapshot it if the data matters, then delete the volume."))
    return out


def find_idle_elastic_ips(ec2) -> List[Finding]:
    out = []
    for a in ec2.describe_addresses().get("Addresses", []):
        if a.get("AssociationId") or a.get("InstanceId") or a.get("NetworkInterfaceId"):
            continue
        out.append(Finding("idle_elastic_ip", a.get("AllocationId") or a.get("PublicIp", "?"),
                           f"{a.get('PublicIp', '?')} is not associated with anything",
                           PRICES["elastic_ip_month"],
                           "Release it if nothing needs that fixed address."))
    return out


def find_old_snapshots(ec2, now: datetime, max_age_days: int = 90) -> List[Finding]:
    out = []
    for s in _paginate(ec2, "describe_snapshots", "Snapshots", OwnerIds=["self"]):
        age = _age_days(s["StartTime"], now)
        if age <= max_age_days:
            continue
        desc = s.get("Description", "") or ""
        backs_ami = "createimage" in desc.lower().replace(" ", "")
        note = " Looks like an AMI backing snapshot: deregister the AMI first." if backs_ami else ""
        out.append(Finding("old_snapshot", s["SnapshotId"],
                           f"{s.get('VolumeSize', '?')} GiB, {age} days old",
                           round(s.get("VolumeSize", 0) * PRICES["snapshot_gb_month"], 2),
                           "Check whether a retention policy needs it; delete if not." + note))
    return out


def find_untagged_running_instances(ec2, now: datetime, min_age_days: int = 30) -> List[Finding]:
    out = []
    for reservation in _paginate(ec2, "describe_instances", "Reservations",
                                 Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
        for i in reservation.get("Instances", []):
            if "Owner" in _tags(i):
                continue
            age = _age_days(i["LaunchTime"], now)
            if age < min_age_days:
                continue
            out.append(Finding("untagged_running_instance", i["InstanceId"],
                               f"{i.get('InstanceType', '?')}, running {age} days, no Owner tag",
                               0.0,
                               "Find the owner, add an Owner tag, stop it if it is not needed."))
    return out


# --------------------------------------------------------------------------- orchestration
def scan(ec2, now: Optional[datetime] = None, snapshot_age_days: int = 90,
         instance_age_days: int = 30) -> List[Finding]:
    now = now or datetime.now(timezone.utc)
    findings = (find_unattached_volumes(ec2) + find_idle_elastic_ips(ec2)
                + find_old_snapshots(ec2, now, snapshot_age_days)
                + find_untagged_running_instances(ec2, now, instance_age_days))
    return sorted(findings, key=lambda f: (-f.est_monthly_usd, f.kind, f.resource_id))


def format_report(findings: List[Finding], region: str) -> str:
    total = sum(f.est_monthly_usd for f in findings)
    lines = [f"AWS cost guard - region {region}", f"{len(findings)} finding(s), "
             f"estimated waste about ${total:,.2f}/month (rough list-price estimate)", ""]
    for f in findings:
        cost = f"${f.est_monthly_usd:>7.2f}" if f.est_monthly_usd else "   n/a  "
        lines.append(f"{cost}  {f.kind:<26} {f.resource_id:<24} {f.detail}")
        lines.append(f"{'':>9}  -> {f.suggestion}")
    if not findings:
        lines.append("Nothing found.")
    return "\n".join(lines)


def make_client(region: str, profile: Optional[str] = None):
    try:
        import boto3                                     # imported lazily so tests need no AWS SDK
    except ImportError:
        raise SystemExit("boto3 is required: pip install boto3")
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("ec2")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read-only AWS cost leak scanner.")
    ap.add_argument("--region", required=True)
    ap.add_argument("--profile", help="AWS CLI profile name")
    ap.add_argument("--snapshot-age-days", type=int, default=90)
    ap.add_argument("--instance-age-days", type=int, default=30)
    ap.add_argument("--json", metavar="FILE", help="also write findings as JSON")
    args = ap.parse_args(argv)

    findings = scan(make_client(args.region, args.profile),
                    snapshot_age_days=args.snapshot_age_days,
                    instance_age_days=args.instance_age_days)
    print(format_report(findings, args.region))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([asdict(f) for f in findings], fh, indent=2)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
