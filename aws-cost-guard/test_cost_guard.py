"""Offline tests: a fake EC2 client stands in for boto3. Run: pytest -q"""
import json
from datetime import datetime, timedelta, timezone

import cost_guard as cg

NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return iter(self.pages)


class FakeEC2:
    """Records every call so tests can prove only Describe* operations are used."""
    def __init__(self, volumes=(), addresses=(), snapshots=(), reservations=(), pages=1):
        self.calls = []
        self._data = {"describe_volumes": ("Volumes", list(volumes)),
                      "describe_snapshots": ("Snapshots", list(snapshots)),
                      "describe_instances": ("Reservations", list(reservations))}
        self._addresses = list(addresses)
        self._pages = pages

    def get_paginator(self, op):
        self.calls.append(op)
        key, items = self._data[op]
        n = max(1, self._pages)
        chunks = [items[i::n] for i in range(n)]          # split across pages
        return FakePaginator([{key: c} for c in chunks])

    def describe_addresses(self):
        self.calls.append("describe_addresses")
        return {"Addresses": self._addresses}

    def __getattr__(self, name):                          # any other API call is a test failure
        raise AssertionError(f"unexpected EC2 call: {name}")


def vol(vid, size, vtype="gp3", state="available", tags=None):
    return {"VolumeId": vid, "Size": size, "VolumeType": vtype, "State": state, "Tags": tags or []}


def snap(sid, size, days, desc=""):
    return {"SnapshotId": sid, "VolumeSize": size, "StartTime": NOW - timedelta(days=days), "Description": desc}


def inst(iid, days, tags=None, itype="t3.micro"):
    return {"InstanceId": iid, "InstanceType": itype, "LaunchTime": NOW - timedelta(days=days), "Tags": tags or []}


def test_unattached_volume_cost_uses_type_price():
    f = cg.find_unattached_volumes(FakeEC2(volumes=[vol("v-1", 100, "gp3")]))
    assert len(f) == 1 and f[0].est_monthly_usd == 8.0 and "100 GiB gp3" in f[0].detail


def test_attached_volume_is_ignored_and_unknown_type_uses_default():
    f = cg.find_unattached_volumes(FakeEC2(volumes=[vol("v-1", 10, state="in-use"), vol("v-2", 10, "weird")]))
    assert [x.resource_id for x in f] == ["v-2"] and f[0].est_monthly_usd == 1.0


def test_elastic_ip_only_unassociated_counted():
    eips = [{"AllocationId": "eipalloc-1", "PublicIp": "1.1.1.1"},
            {"AllocationId": "eipalloc-2", "PublicIp": "2.2.2.2", "AssociationId": "eipassoc-9"},
            {"AllocationId": "eipalloc-3", "PublicIp": "3.3.3.3", "InstanceId": "i-1"}]
    f = cg.find_idle_elastic_ips(FakeEC2(addresses=eips))
    assert [x.resource_id for x in f] == ["eipalloc-1"] and f[0].est_monthly_usd == 3.65


def test_snapshot_age_boundary_and_ami_note():
    ec2 = FakeEC2(snapshots=[snap("s-new", 50, 90), snap("s-old", 50, 91),
                             snap("s-ami", 8, 400, "Created by CreateImage(i-1) for ami-1")])
    f = {x.resource_id: x for x in cg.find_old_snapshots(ec2, NOW, 90)}
    assert set(f) == {"s-old", "s-ami"}                     # exactly 90 days is not "older than 90"
    assert f["s-old"].est_monthly_usd == 2.5
    assert "AMI" in f["s-ami"].suggestion and "AMI" not in f["s-old"].suggestion


def test_untagged_running_instances():
    res = [{"Instances": [inst("i-a", 100), inst("i-b", 100, [{"Key": "Owner", "Value": "anas"}]),
                          inst("i-c", 5)]}]
    f = cg.find_untagged_running_instances(FakeEC2(reservations=res), NOW, 30)
    assert [x.resource_id for x in f] == ["i-a"]


def test_multiple_pages_are_all_read():
    vols = [vol(f"v-{i}", 10) for i in range(7)]
    assert len(cg.find_unattached_volumes(FakeEC2(volumes=vols, pages=3))) == 7


def test_scan_sorts_by_cost_and_only_describe_calls_are_made():
    ec2 = FakeEC2(volumes=[vol("v-1", 10), vol("v-2", 500)], addresses=[{"AllocationId": "e-1", "PublicIp": "1.1.1.1"}],
                  snapshots=[snap("s-1", 100, 200)],
                  reservations=[{"Instances": [inst("i-1", 60)]}])
    findings = cg.scan(ec2, now=NOW)
    assert [f.resource_id for f in findings][0] == "v-2"       # $40 is the biggest
    assert [f.est_monthly_usd for f in findings] == sorted((f.est_monthly_usd for f in findings), reverse=True)
    assert set(ec2.calls) == {"describe_volumes", "describe_addresses", "describe_snapshots", "describe_instances"}


def test_report_text_and_empty_report():
    f = cg.scan(FakeEC2(volumes=[vol("v-1", 100)]), now=NOW)
    text = cg.format_report(f, "ap-south-1")
    assert "ap-south-1" in text and "$8.00" in text and "unattached_volume" in text
    assert "Nothing found." in cg.format_report([], "ap-south-1")


def test_iam_policy_is_describe_only():
    with open("iam-policy.json") as fh:
        actions = [a for s in json.load(fh)["Statement"] for a in s["Action"]]
    assert actions and all(a.startswith("ec2:Describe") for a in actions)
