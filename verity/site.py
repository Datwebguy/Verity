"""Generate the static public site (no JS, no accounts): docs/index.html and docs/r/<id>.html."""
import html
import json
import os

from . import store
from .config import site_dir

CSS = """
:root{--bg:#fff;--fg:#14171a;--mut:#5b6670;--card:#f4f6f8;--line:#dde2e7;--ok:#0a7d3c;--bad:#b3261e;--pend:#8a6d00}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#8b98a5;--card:#161b22;--line:#2b333b;--ok:#4cc38a;--bad:#ff7b72;--pend:#e3b341}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 64px}a{color:inherit}
h1{margin:0 0 4px;font-size:1.8rem}.mut{color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:baseline;justify-content:space-between}
.tag{font-weight:600;padding:2px 8px;border:1px solid var(--line);border-radius:99px;font-size:.85rem}
.correct{color:var(--ok)}.incorrect{color:var(--bad)}.pending{color:var(--pend)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.stat b{display:block;font-size:1.5rem}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:6px 4px;border-bottom:1px solid var(--line);vertical-align:top;font-size:.92rem}
pre{overflow:auto;background:var(--bg);border:1px solid var(--line);padding:10px;border-radius:8px;font-size:.8rem;max-height:360px}
code{word-break:break-all}.warn{border-left:4px solid var(--bad)}
"""
DISCLAIMER = "Practice decisions only. No real orders are placed. Not financial advice."


def e(x):
    return html.escape("" if x is None else str(x))


def page(title, body):
    return ("<!doctype html><html lang=en><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>%s</title><style>%s</style></head><body><main>%s"
            "<p class=mut>%s</p></main></body></html>" % (e(title), CSS, body, e(DISCLAIMER)))


def scoreboard(receipts):
    graded = [r for r in receipts if r["grade"] in ("correct", "incorrect")]
    n = len(graded)
    correct = sum(r["grade"] == "correct" for r in graded)
    rets = [r["grade_return_pct"] for r in graded if r.get("grade_return_pct") is not None]
    base = sum(x > 0 for x in rets)
    hi = [r for r in graded if r["confidence"] >= 0.5]
    lo = [r for r in graded if r["confidence"] < 0.5]
    pct = lambda a, b: ("%.0f%% (%d/%d)" % (100.0 * a / b, a, b)) if b else "n/a"
    return {
        "total": len(receipts), "graded": n, "pending": len(receipts) - n,
        "hit": pct(correct, n),
        "baseline": pct(base, len(rets)),
        "hi": pct(sum(r["grade"] == "correct" for r in hi), len(hi)),
        "lo": pct(sum(r["grade"] == "correct" for r in lo), len(lo)),
    }


def grade_badge(r):
    g = r["grade"]
    extra = ""
    if g == "pending" and r.get("grade_note"):
        extra = " <span class=mut>(%s)</span>" % e(r["grade_note"])
    return "<span class='tag %s'>%s</span>%s" % (e(g), e(g), extra)


def index_html(receipts):
    s = scoreboard(receipts)
    cards = []
    for r in receipts:
        failed = [t for t in r["tools"] if t["status"] != "ok"]
        cards.append(
            "<div class=card><div class=row><a href='r/%s.html'><b>%s</b> &middot; %s</a>%s</div>"
            "<div class=mut>%s &middot; confidence %.2f%s</div><p>%s</p></div>" % (
                e(r["id"]), e(r["symbol"]), e(r["practice_action"]), grade_badge(r),
                e(r["timestamp"]), r["confidence"],
                " &middot; <span class=incorrect>%d tool(s) not ok</span>" % len(failed) if failed else "",
                e(r["thesis"])))
    body = (
        "<h1>Verity</h1><p class=mut>An autonomous agent that publishes practice decisions from live "
        "RYO-CHAN research tools, then grades them against real later price movement.</p>"
        "<div class='card stats'>"
        "<div class=stat><b>%d</b>receipts</div><div class=stat><b>%d</b>graded</div>"
        "<div class=stat><b>%d</b>pending</div><div class=stat><b>%s</b>hit rate</div>"
        "<div class=stat><b>%s</b>'always long' baseline</div></div>"
        "<div class='card mut'>Confidence check &mdash; calls at confidence &ge; 0.5: %s correct; below 0.5: %s correct.</div>"
        "%s" % (s["total"], s["graded"], s["pending"], e(s["hit"]), e(s["baseline"]), e(s["hi"]), e(s["lo"]),
                "".join(cards) or "<div class=card>No receipts yet. Run <code>python -m verity receipt BTC</code>.</div>"))
    return page("Verity", body)


def receipt_html(r):
    rows = "".join("<tr><td>%s</td><td class=%s>%s</td><td>%s</td></tr>" % (
        e(t["name"]), "correct" if t["status"] == "ok" else "incorrect", e(t["status"]), e(t.get("detail")))
        for t in r["tools"])
    ok = store.verify(r)
    body = (
        "<p><a href='../index.html'>&larr; all receipts</a></p>"
        "<h1>%s &middot; %s</h1><div class=row><span class=mut>%s</span>%s</div>"
        "<div class=card><b>Thesis</b><p>%s</p><b>Evidence summary</b><p>%s</p>"
        "<table><tr><th>Entry price</th><td>%s</td></tr><tr><th>Confidence</th><td>%.2f</td></tr>"
        "<tr><th>Invalidation</th><td>%s</td></tr><tr><th>Grade window</th><td>%s h</td></tr>"
        "<tr><th>Grade</th><td>%s</td></tr><tr><th>Grade timestamp</th><td>%s</td></tr>"
        "<tr><th>Grade price / return</th><td>%s / %s%%</td></tr><tr><th>Grade note</th><td>%s</td></tr></table></div>"
        "<div class=card><b>Tools called</b><table><tr><th>Tool</th><th>Status</th><th>Detail</th></tr>%s</table></div>"
        "<div class='card%s'><b>Integrity</b><br><code>sha256 %s</code><br>%s</div>"
        "<div class=card><details><summary><b>Raw evidence</b> (stored tool responses)</summary><pre>%s</pre></details></div>" % (
            e(r["symbol"]), e(r["practice_action"]), e(r["timestamp"]), grade_badge(r),
            e(r["thesis"]), e(r["evidence_summary"]), e(r["entry_price"]), r["confidence"],
            e(r["invalidation"]), e(r["grade_window_hours"]), e(r["grade"]), e(r["grade_timestamp"]),
            e(r["grade_price"]), e(r["grade_return_pct"]), e(r["grade_note"]), rows,
            "" if ok else " warn", e(r["receipt_hash"]),
            "Body matches its hash." if ok else "WARNING: body does not match its hash.",
            e(json.dumps(r["raw_evidence"], indent=2, ensure_ascii=False))))
    return page("%s %s — Verity" % (r["symbol"], r["practice_action"]), body)


def build(root=None, out=None):
    receipts = store.all_receipts(root)
    out = out or site_dir()
    os.makedirs(os.path.join(out, "r"), exist_ok=True)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html(receipts))
    for r in receipts:
        with open(os.path.join(out, "r", r["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(receipt_html(r))
    with open(os.path.join(out, "receipts.json"), "w", encoding="utf-8") as f:
        json.dump(receipts, f, indent=2, sort_keys=True, ensure_ascii=False)
    return len(receipts)
