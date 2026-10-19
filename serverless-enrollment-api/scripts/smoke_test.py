"""
End-to-end test of the LIVE API. Standard library only, so it runs anywhere
Python 3 runs (Windows, CloudShell, a laptop).

    python scripts/smoke_test.py <ApiUrl> <ApiToken>

It enrolls 6 demo subjects, checks every route and every error code, then
deletes the demo subjects again so the table is left as it was.
"""

import json
import sys
import urllib.error
import urllib.request

DEMO = [
    {"studyid": "DEMO01", "siteid": "701", "subjid": "1015", "armcd": "PBO",   "sex": "F", "age": 63, "icdtc": "2026-01-02"},
    {"studyid": "DEMO01", "siteid": "701", "subjid": "1023", "armcd": "XANHI", "sex": "M", "age": 64, "icdtc": "2026-01-05"},
    {"studyid": "DEMO01", "siteid": "701", "subjid": "1028", "armcd": "XANLO", "sex": "M", "age": 71, "icdtc": "2026-01-19"},
    {"studyid": "DEMO01", "siteid": "702", "subjid": "1047", "armcd": "PBO",   "sex": "F", "age": 85, "icdtc": "2026-02-12"},
    {"studyid": "DEMO01", "siteid": "702", "subjid": "1057", "armcd": "XANHI", "sex": "F", "age": 59, "icdtc": "2026-02-14"},
    {"studyid": "DEMO01", "siteid": "702", "subjid": "1097", "armcd": "XANLO", "sex": "M", "age": 68, "icdtc": "2026-03-01"},
]


def call(base, method, path, body=None, token=None):
    req = urllib.request.Request(base.rstrip("/") + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("content-type", "application/json")
    if token:
        req.add_header("x-api-token", token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main(base, token):
    results = []

    def check(name, got, want):
        ok = got == want
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name:<48} HTTP {got}")

    s, _ = call(base, "GET", "/health")
    check("GET /health", s, 200)

    for d in DEMO:
        s, b = call(base, "POST", "/subjects", d, token)
        check(f"POST /subjects  enroll {d['siteid']}-{d['subjid']}", s, 201)

    s, b = call(base, "POST", "/subjects", DEMO[0], token)
    check("POST duplicate subject -> 409", s, 409)
    s, b = call(base, "POST", "/subjects", DEMO[0])
    check("POST without token -> 401", s, 401)
    bad = dict(DEMO[0], subjid="9", armcd="DRUG", age=12, icdtc="02/01/2026")
    s, b = call(base, "POST", "/subjects", bad, token)
    check("POST invalid data -> 400", s, 400)
    print("      validation errors returned:", b.get("errors"))

    s, b = call(base, "GET", "/subjects/DEMO01-701-1015")
    check("GET /subjects/DEMO01-701-1015", s, 200)
    s, _ = call(base, "GET", "/subjects/DEMO01-999-0000")
    check("GET unknown subject -> 404", s, 404)
    s, b = call(base, "GET", "/subjects?siteid=702")
    check("GET /subjects?siteid=702", s, 200)

    s, summary = call(base, "GET", "/summary")
    check("GET /summary", s, 200)
    print("      summary:", json.dumps(summary))

    for d in DEMO:
        s, _ = call(base, "DELETE", f"/subjects/DEMO01-{d['siteid']}-{d['subjid']}", token=token)
        check(f"DELETE demo subject {d['siteid']}-{d['subjid']}", s, 200)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/smoke_test.py <ApiUrl> <ApiToken>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
