"""Build the adverse-event report website from the raw CSVs (standard library only).

Rules (same as the SAS program in sas/):
  * Safety population = subjects with a first dose date
  * Treatment-emergent AE = AE start date on or after first dose date
  * A subject is counted once per preferred term
  * Percent = subjects with the event / safety subjects in that arm

Usage:  python python/build_report.py            writes site/index.html and site/ae_summary.csv
"""
import csv, html, pathlib
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARMS = ["Placebo", "Drug 10 mg"]

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def iso(s):
    try:
        return date.fromisoformat((s or "").strip())
    except ValueError:
        return None

def compute(dm, ae):
    """Return (denominators, rows). rows = [(soc, term, {arm: n})] sorted by SOC then term."""
    safety = {}
    for r in dm:
        first = iso(r["FIRSTDOSE"])
        if first and r["ARM"] in ARMS:
            safety[r["SUBJID"]] = (r["ARM"], first)
    denom = {a: sum(1 for arm, _ in safety.values() if arm == a) for a in ARMS}
    seen = {}  # (soc, term, arm) -> set of subjects
    for r in ae:
        sub = safety.get(r["SUBJID"])
        start = iso(r["AESTDTC"])
        if not sub or not start or start < sub[1]:
            continue  # not in safety population, bad date, or before first dose
        seen.setdefault((r["AEBODSYS"], r["AETERM"], sub[0]), set()).add(r["SUBJID"])
    keys = sorted({(soc, term) for soc, term, _ in seen})
    rows = [(soc, term, {a: len(seen.get((soc, term, a), ())) for a in ARMS}) for soc, term in keys]
    return denom, rows

def cell(n, big_n):
    return "0" if n == 0 else f"{n} ({100 * n / big_n:.1f}%)"

def write_csv(path, denom, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["System Organ Class", "Preferred Term"] + [f"{a} (N={denom[a]})" for a in ARMS])
        for soc, term, c in rows:
            w.writerow([soc, term] + [cell(c[a], denom[a]) for a in ARMS])

def bar_chart(denom, rows):
    """Inline SVG: percent of subjects per term, both arms."""
    rows = sorted(rows, key=lambda r: -max(100 * r[2][a] / denom[a] for a in ARMS))
    lh, left, W = 34, 230, 760
    H = 40 + lh * len(rows)
    scale = (W - left - 60) / 60.0  # 0-60 %
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Percent of subjects with each adverse event, by arm" xmlns="http://www.w3.org/2000/svg">']
    for t in (0, 20, 40, 60):
        x = left + t * scale
        out.append(f'<line x1="{x}" y1="24" x2="{x}" y2="{H-6}" class="grid"/><text x="{x}" y="14" class="tick">{t}%</text>')
    for i, (_, term, c) in enumerate(rows):
        y = 30 + i * lh
        out.append(f'<text x="{left-10}" y="{y+16}" text-anchor="end" class="lbl">{html.escape(term)}</text>')
        for j, a in enumerate(ARMS):
            pct = 100 * c[a] / denom[a]
            w = max(pct * scale, 0)
            cls = "b0" if j == 0 else "b1"
            out.append(f'<rect x="{left}" y="{y+j*13}" width="{w:.1f}" height="11" class="{cls}" rx="2"><title>{a}: {pct:.1f}%</title></rect>')
            out.append(f'<text x="{left+w+5}" y="{y+j*13+10}" class="val">{pct:.1f}%</text>')
    out.append("</svg>")
    return "\n".join(out)

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adverse Event Summary (synthetic data)</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#667085;--line:#e4e7ec;--b0:#98a2b3;--b1:#ff9900;--warn:#fff4db}}
@media (prefers-color-scheme:dark){{:root{{--bg:#10151c;--card:#18202a;--ink:#e8edf3;--mute:#9aa6b5;--line:#2a3441;--b0:#7b8798;--warn:#3a2f12}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:32px 16px 56px}}
h1{{margin:0 0 4px;font-size:1.7rem}} h2{{font-size:1.05rem;margin:28px 0 8px}}
.sub{{color:var(--mute);margin:0 0 16px}}
.note{{background:var(--warn);border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:.92rem}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.92rem}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}}
th{{color:var(--mute);font-weight:600}} td.n,th.n{{text-align:center;white-space:nowrap}}
svg{{width:100%;height:auto}} .grid{{stroke:var(--line)}} .tick,.val{{fill:var(--mute);font-size:11px}} .lbl{{fill:var(--ink);font-size:13px}}
.b0{{fill:var(--b0)}} .b1{{fill:var(--b1)}}
.legend{{display:flex;gap:16px;font-size:.88rem;color:var(--mute);margin:0 0 6px}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
footer{{margin-top:28px;color:var(--mute);font-size:.85rem}}
</style></head><body><main>
<h1>Adverse Event Summary</h1>
<p class="sub">Subjects with treatment-emergent adverse events, safety population</p>
<p class="note"><b>Synthetic practice data.</b> No real patients. Built from the same rules as the SAS program in this project.</p>
<h2>Percent of subjects by event</h2>
<div class="card">
<div class="legend"><span><i style="background:var(--b0)"></i>Placebo (N={n0})</span><span><i style="background:var(--b1)"></i>Drug 10 mg (N={n1})</span></div>
{chart}
</div>
<h2>Table</h2>
<div class="card"><table>
<tr><th>System Organ Class</th><th>Preferred Term</th><th class="n">Placebo<br>(N={n0})</th><th class="n">Drug 10 mg<br>(N={n1})</th></tr>
{rows}
</table></div>
<p><a href="ae_summary.csv">Download as CSV</a></p>
<footer>Generated {today} by build_report.py. Hosted on Amazon S3 static website hosting.</footer>
</main></body></html>
"""

def write_html(path, denom, rows):
    body = "\n".join(
        f"<tr><td>{html.escape(soc)}</td><td>{html.escape(term)}</td>"
        + "".join(f'<td class="n">{cell(c[a], denom[a])}</td>' for a in ARMS) + "</tr>"
        for soc, term, c in rows)
    page = PAGE.format(n0=denom[ARMS[0]], n1=denom[ARMS[1]], chart=bar_chart(denom, rows),
                       rows=body, today=date.today().isoformat())
    pathlib.Path(path).write_text(page, encoding="utf-8")

def main():
    dm = read_csv(ROOT / "data" / "dm_raw.csv")
    ae = read_csv(ROOT / "data" / "ae_raw.csv")
    denom, rows = compute(dm, ae)
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    write_csv(out / "ae_summary.csv", denom, rows)
    write_html(out / "index.html", denom, rows)
    print(f"Safety population: {denom}")
    print(f"Wrote {out/'index.html'} and {out/'ae_summary.csv'} ({len(rows)} terms)")

if __name__ == "__main__":
    main()
