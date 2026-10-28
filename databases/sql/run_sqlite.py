"""Load the practice database into SQLite and run every query in 03_queries.sql.
Usage:  python sql/run_sqlite.py        (Python 3.9+, nothing to install)"""
import sqlite3, pathlib

here = pathlib.Path(__file__).parent
db = sqlite3.connect(":memory:")
for name in ("01_schema.sql", "02_data.sql"):
    db.executescript((here / name).read_text())

queries = (here / "03_queries.sql").read_text().split(";")
n = 0
for q in queries:
    lines = [l for l in q.splitlines() if l.strip()]
    comments = [l for l in lines if l.startswith("--")]
    title = comments[-1] if comments else ""
    body = "\n".join(l for l in lines if not l.startswith("--")).strip()
    if not body:
        continue
    n += 1
    cur = db.execute(body)
    print(f"\n#{n} {title.lstrip('- ').strip()}")
    print(" | ".join(d[0] for d in cur.description))
    for row in cur.fetchall()[:8]:
        print(" | ".join(str(v) for v in row))
