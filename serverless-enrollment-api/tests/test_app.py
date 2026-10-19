"""Unit tests for the enrollment API. Run with:  python -m pytest -q

DynamoDB is replaced by FakeTable, an in-memory dict that behaves like the
four table calls the app uses, so the tests need no AWS account and no boto3.
"""

import json
import pathlib
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import app  # noqa: E402

TOKEN = "test-token-1234567890"


class ConditionalCheckFailed(Exception):
    response = {"Error": {"Code": "ConditionalCheckFailedException"}}


class FakeTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item, ConditionExpression=None):
        if ConditionExpression and Item["usubjid"] in self.items:
            raise ConditionalCheckFailed()
        self.items[Item["usubjid"]] = dict(Item)

    def get_item(self, Key):
        item = self.items.get(Key["usubjid"])
        return {"Item": dict(item)} if item else {}

    def delete_item(self, Key, ConditionExpression=None):
        if ConditionExpression and Key["usubjid"] not in self.items:
            raise ConditionalCheckFailed()
        self.items.pop(Key["usubjid"], None)

    def scan(self, **kwargs):
        return {"Items": [dict(i) for i in self.items.values()]}


def setup_function():
    app._table = FakeTable()
    app.os.environ["API_TOKEN"] = TOKEN


def call(route, body=None, path=None, query=None, token=TOKEN):
    event = {"routeKey": route, "headers": {}, "pathParameters": path,
             "queryStringParameters": query}
    if token:
        event["headers"]["x-api-token"] = token
    if body is not None:
        event["body"] = json.dumps(body)
    res = app.handler(event, None)
    return res["statusCode"], json.loads(res["body"])


def subject(**over):
    s = {"studyid": "CDISCPILOT01", "siteid": "701", "subjid": "1015",
         "armcd": "PBO", "sex": "F", "age": 63, "icdtc": "2026-01-02"}
    s.update(over)
    return s


# ------------------------------------------------------------------ tests
def test_health():
    assert call("GET /health", token=None) == (200, {"status": "ok"})


def test_enroll_derives_usubjid_and_arm():
    status, body = call("POST /subjects", subject())
    assert status == 201
    assert body["usubjid"] == "CDISCPILOT01-701-1015"
    assert body["arm"] == "Placebo"


def test_enroll_normalises_case():
    status, body = call("POST /subjects", subject(studyid="cdiscpilot01", armcd="xanhi", sex="m"))
    assert status == 201
    assert (body["studyid"], body["armcd"], body["sex"]) == ("CDISCPILOT01", "XANHI", "M")


def test_duplicate_enrollment_is_rejected():
    call("POST /subjects", subject())
    status, body = call("POST /subjects", subject(age=70))
    assert status == 409
    assert app._table.items["CDISCPILOT01-701-1015"]["age"] == 63  # not overwritten


def test_write_needs_the_right_token():
    assert call("POST /subjects", subject(), token=None)[0] == 401
    assert call("POST /subjects", subject(), token="wrong-token-000000")[0] == 401
    assert call("DELETE /subjects/{usubjid}", path={"usubjid": "X"}, token=None)[0] == 401
    assert app._table.items == {}


def test_validation_reports_every_problem():
    bad = subject(siteid="7", subjid="15", armcd="DRUG", sex="X", age=12, icdtc="02/01/2026")
    status, body = call("POST /subjects", bad)
    assert status == 400
    text = " ".join(body["errors"])
    for word in ("siteid", "subjid", "armcd", "sex", "age", "icdtc"):
        assert word in text, word


def test_missing_and_unknown_fields():
    s = subject(country="IND")
    del s["age"]
    status, body = call("POST /subjects", s)
    assert status == 400
    assert any("Unknown" in e for e in body["errors"])
    assert any("Missing" in e and "age" in e for e in body["errors"])


def test_impossible_and_future_dates():
    assert call("POST /subjects", subject(icdtc="2026-02-30"))[0] == 400
    _, errors = app.validate_subject(subject(icdtc="2026-05-01"), today=date(2026, 4, 1))
    assert errors == ["icdtc cannot be in the future."]


def test_age_must_be_a_whole_number():
    for age in ("63", 63.5, True):
        assert call("POST /subjects", subject(age=age))[0] == 400


def test_bad_json_body():
    event = {"routeKey": "POST /subjects", "headers": {"x-api-token": TOKEN}, "body": "{not json"}
    assert app.handler(event, None)["statusCode"] == 400


def test_get_list_filter_and_404():
    call("POST /subjects", subject())
    call("POST /subjects", subject(siteid="702", subjid="1047", armcd="XANLO"))
    assert call("GET /subjects")[1]["count"] == 2
    status, body = call("GET /subjects", query={"siteid": "702"})
    assert body["count"] == 1 and body["subjects"][0]["subjid"] == "1047"
    status, body = call("GET /subjects/{usubjid}", path={"usubjid": "cdiscpilot01-701-1015"})
    assert status == 200 and body["sex"] == "F"
    assert call("GET /subjects/{usubjid}", path={"usubjid": "NOPE-000-0000"})[0] == 404


def test_delete():
    call("POST /subjects", subject())
    assert call("DELETE /subjects/{usubjid}", path={"usubjid": "CDISCPILOT01-701-1015"}) == \
        (200, {"deleted": "CDISCPILOT01-701-1015"})
    assert call("DELETE /subjects/{usubjid}", path={"usubjid": "CDISCPILOT01-701-1015"})[0] == 404


def test_summary():
    assert call("GET /summary")[1] == {"total": 0, "by_arm": {}, "by_site": {}, "by_sex": {}, "age": None}
    call("POST /subjects", subject(age=60))
    call("POST /subjects", subject(subjid="1023", armcd="XANHI", sex="M", age=70))
    call("POST /subjects", subject(siteid="702", subjid="1047", age=80))
    body = call("GET /summary")[1]
    assert body["total"] == 3
    assert body["by_site"] == {"701": {"PBO": 1, "XANHI": 1}, "702": {"PBO": 1}}
    assert body["by_sex"] == {"F": 2, "M": 1}
    assert body["age"] == {"mean": 70.0, "min": 60, "max": 80}


def test_unknown_route_and_crash_are_handled():
    assert call("PUT /subjects")[0] == 404
    app._table = None  # forces a real-table lookup, which fails without AWS
    app.os.environ.pop("TABLE_NAME", None)
    assert call("GET /subjects")[0] == 500
