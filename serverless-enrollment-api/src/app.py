"""
Clinical Trial Enrollment API - AWS Lambda handler.

API Gateway (HTTP API, payload format 2.0) sends every request here.
Routes are matched on event["routeKey"], e.g. "GET /subjects/{usubjid}".

    GET    /health                 liveness check (no token)
    GET    /subjects               list subjects (optional ?siteid=701)
    GET    /subjects/{usubjid}     one subject
    GET    /summary                enrollment summary by site, arm, sex, age
    POST   /subjects               enroll a subject          (needs x-api-token)
    DELETE /subjects/{usubjid}     remove a subject          (needs x-api-token)

Data lives in one DynamoDB table whose partition key is USUBJID
(STUDYID-SITEID-SUBJID, the same derivation used in SDTM DM).
"""

import base64
import hmac
import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

log = logging.getLogger()
log.setLevel(logging.INFO)

ARMS = {
    "PBO": "Placebo",
    "XANLO": "Xanomeline Low Dose",
    "XANHI": "Xanomeline High Dose",
}
SEXES = {"M", "F", "U"}
MIN_AGE, MAX_AGE = 18, 100
FIELDS = {"studyid", "siteid", "subjid", "armcd", "sex", "age", "icdtc"}

_table = None  # created on first use; tests replace it with a fake


def get_table():
    global _table
    if _table is None:
        import boto3  # imported lazily so unit tests run without boto3
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


# ---------------------------------------------------------------- helpers
def _json_default(o):
    if isinstance(o, Decimal):  # DynamoDB returns numbers as Decimal
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"Not JSON serialisable: {type(o)}")


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }


def _authorised(event):
    expected = os.environ.get("API_TOKEN", "")
    given = (event.get("headers") or {}).get("x-api-token", "")
    # compare_digest takes the same time whatever the input, so an attacker
    # cannot guess the token one character at a time from response timings
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


def _body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    return json.loads(raw) if raw else None


def _error_code(exc):
    return getattr(exc, "response", {}).get("Error", {}).get("Code")


# ------------------------------------------------------------- validation
def validate_subject(data, today=None):
    """Return (clean_record, errors). errors is a list of strings."""
    today = today or date.today()
    if not isinstance(data, dict):
        return None, ["Body must be a JSON object."]

    errors = []
    unknown = set(data) - FIELDS
    if unknown:
        errors.append(f"Unknown field(s): {', '.join(sorted(unknown))}.")
    missing = [f for f in sorted(FIELDS) if f not in data or data[f] in ("", None)]
    if missing:
        errors.append(f"Missing required field(s): {', '.join(missing)}.")
        return None, errors

    studyid = str(data["studyid"]).strip().upper()
    siteid = str(data["siteid"]).strip()
    subjid = str(data["subjid"]).strip()
    armcd = str(data["armcd"]).strip().upper()
    sex = str(data["sex"]).strip().upper()
    icdtc = str(data["icdtc"]).strip()

    if not re.fullmatch(r"[A-Z0-9]{1,20}", studyid):
        errors.append("studyid must be 1-20 letters or digits.")
    if not re.fullmatch(r"\d{3}", siteid):
        errors.append("siteid must be exactly 3 digits, e.g. 701.")
    if not re.fullmatch(r"\d{4}", subjid):
        errors.append("subjid must be exactly 4 digits, e.g. 1015.")
    if armcd not in ARMS:
        errors.append(f"armcd must be one of {', '.join(ARMS)}.")
    if sex not in SEXES:
        errors.append("sex must be M, F or U.")

    age = data["age"]
    if isinstance(age, bool) or not isinstance(age, int):
        errors.append("age must be a whole number.")
    elif not MIN_AGE <= age <= MAX_AGE:
        errors.append(f"age must be between {MIN_AGE} and {MAX_AGE} (adult study).")

    try:
        consent = date.fromisoformat(icdtc) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", icdtc) else None
    except ValueError:
        consent = None
    if consent is None:
        errors.append("icdtc (informed consent date) must be a real date as YYYY-MM-DD.")
    elif consent > today:
        errors.append("icdtc cannot be in the future.")

    if errors:
        return None, errors

    return {
        "usubjid": f"{studyid}-{siteid}-{subjid}",
        "studyid": studyid,
        "siteid": siteid,
        "subjid": subjid,
        "armcd": armcd,
        "arm": ARMS[armcd],
        "sex": sex,
        "age": age,
        "icdtc": icdtc,
        "enrolled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, []


# ----------------------------------------------------------------- routes
def health(event):
    return respond(200, {"status": "ok"})


def enroll(event):
    if not _authorised(event):
        return respond(401, {"error": "Missing or wrong x-api-token header."})
    try:
        data = _body(event)
    except (ValueError, UnicodeDecodeError):
        return respond(400, {"errors": ["Body is not valid JSON."]})
    record, errors = validate_subject(data)
    if errors:
        return respond(400, {"errors": errors})
    try:
        # the condition makes the write fail if this USUBJID already exists,
        # so two enrollments of the same subject can never overwrite each other
        get_table().put_item(Item=record, ConditionExpression="attribute_not_exists(usubjid)")
    except Exception as exc:
        if _error_code(exc) == "ConditionalCheckFailedException":
            return respond(409, {"error": f"{record['usubjid']} is already enrolled."})
        raise
    log.info(json.dumps({"action": "enroll", "usubjid": record["usubjid"]}))
    return respond(201, record)


def _scan_all():
    items, kwargs = [], {}
    while True:  # a scan returns at most 1 MB per call, so follow the pages
        page = get_table().scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def list_subjects(event):
    siteid = (event.get("queryStringParameters") or {}).get("siteid")
    items = _scan_all()
    if siteid:
        items = [i for i in items if i.get("siteid") == siteid]
    items.sort(key=lambda i: i["usubjid"])
    return respond(200, {"count": len(items), "subjects": items})


def get_subject(event):
    usubjid = event["pathParameters"]["usubjid"].upper()
    item = get_table().get_item(Key={"usubjid": usubjid}).get("Item")
    if not item:
        return respond(404, {"error": f"{usubjid} not found."})
    return respond(200, item)


def delete_subject(event):
    if not _authorised(event):
        return respond(401, {"error": "Missing or wrong x-api-token header."})
    usubjid = event["pathParameters"]["usubjid"].upper()
    try:
        get_table().delete_item(Key={"usubjid": usubjid},
                                ConditionExpression="attribute_exists(usubjid)")
    except Exception as exc:
        if _error_code(exc) == "ConditionalCheckFailedException":
            return respond(404, {"error": f"{usubjid} not found."})
        raise
    log.info(json.dumps({"action": "delete", "usubjid": usubjid}))
    return respond(200, {"deleted": usubjid})


def summary(event):
    items = _scan_all()
    by_site = defaultdict(Counter)
    for i in items:
        by_site[i["siteid"]][i["armcd"]] += 1
    ages = [int(i["age"]) for i in items]
    return respond(200, {
        "total": len(items),
        "by_arm": dict(Counter(i["armcd"] for i in items)),
        "by_site": {s: dict(c) for s, c in sorted(by_site.items())},
        "by_sex": dict(Counter(i["sex"] for i in items)),
        "age": {
            "mean": round(sum(ages) / len(ages), 1),
            "min": min(ages),
            "max": max(ages),
        } if ages else None,
    })


ROUTES = {
    "GET /health": health,
    "GET /subjects": list_subjects,
    "POST /subjects": enroll,
    "GET /subjects/{usubjid}": get_subject,
    "DELETE /subjects/{usubjid}": delete_subject,
    "GET /summary": summary,
}


def handler(event, context):
    route = ROUTES.get(event.get("routeKey", ""))
    if route is None:
        return respond(404, {"error": "No such route."})
    try:
        return route(event)
    except Exception:
        log.exception("Unhandled error")  # full traceback goes to CloudWatch
        return respond(500, {"error": "Internal error. See CloudWatch Logs."})
