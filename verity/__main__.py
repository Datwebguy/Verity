import argparse
import sys
import time

from . import grade as grading
from . import site, skill, store
from .config import grade_hours, load_env
from .receipt import make_receipt
from .ryo import Client, RyoError


def cmd_receipt(a):
    c = Client()
    for sym in a.symbols:
        r = make_receipt(c, sym, a.hours or grade_hours())
        store.save(r)
        bad = [t for t in r["tools"] if t["status"] != "ok"]
        print("%s %s conf=%.2f  tools ok=%d not_ok=%d  -> %s" % (
            r["symbol"], r["practice_action"], r["confidence"], len(r["tools"]) - len(bad), len(bad), r["id"]))
        for t in bad:
            print("   ! %s: %s (%s)" % (t["name"], t["status"], t["detail"]), file=sys.stderr)
    site.build()


def cmd_grade(a):
    out = grading.grade_due(Client(), force=a.force)
    for r in out:
        print("%s %s -> %s %s" % (r["id"], r["practice_action"], r["grade"], r.get("grade_note") or ""))
    if not out:
        print("nothing pending")
    site.build()


def cmd_tools(a):
    try:
        for n, t in Client().tools().items():
            print("%s: %s" % (n, (t.get("description") or "")[:100]))
            print("   schema:", t.get("inputSchema"))
    except RyoError as e:
        print("RYO %s: %s" % (e.status, e.message), file=sys.stderr)
        sys.exit(1)


def cmd_loop(a):
    syms = [s for s in a.symbols.split(",") if s]
    while True:
        c = Client()
        for s in syms:
            try:
                store.save(make_receipt(c, s, a.hours or grade_hours()))
            except Exception as ex:
                print("receipt failed for %s: %s" % (s, ex), file=sys.stderr)
        grading.grade_due(c)
        print("cycle done, receipts=%d" % site.build())
        if a.once:
            return
        time.sleep(a.every)


def main():
    load_env()
    p = argparse.ArgumentParser(prog="verity")
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("receipt"); s.add_argument("symbols", nargs="+"); s.add_argument("--hours", type=float); s.set_defaults(f=cmd_receipt)
    s = sp.add_parser("grade"); s.add_argument("--force", action="store_true", help="grade now, ignoring the window (demo only)"); s.set_defaults(f=cmd_grade)
    sp.add_parser("build").set_defaults(f=lambda a: print("built", site.build(), "receipts"))
    sp.add_parser("tools").set_defaults(f=cmd_tools)
    s = sp.add_parser("serve"); s.add_argument("--port", type=int, default=8787); s.set_defaults(f=lambda a: skill.serve(port=a.port))
    s = sp.add_parser("loop"); s.add_argument("--symbols", required=True); s.add_argument("--every", type=int, default=3600)
    s.add_argument("--hours", type=float); s.add_argument("--once", action="store_true"); s.set_defaults(f=cmd_loop)
    a = p.parse_args()
    a.f(a)


main()
