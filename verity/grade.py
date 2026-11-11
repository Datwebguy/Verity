"""Grade receipts against real later price movement. Rules are documented in docs/GRADING.md."""
from datetime import datetime, timedelta, timezone

from . import store
from .decide import find_price
from .receipt import now_iso
from .ryo import Client, RyoError

BAND_PCT = 3.0  # a move inside +/- BAND_PCT counts as "no meaningful move"


def _parse(ts):
    return datetime.fromisoformat(ts)


def due(receipt, now=None):
    now = now or datetime.now(timezone.utc)
    return _parse(receipt["timestamp"]) + timedelta(hours=receipt["grade_window_hours"]) <= now


def judge(action, entry, price, invalidation_price):
    """Return (grade, return_pct, note). Pure function."""
    ret = (price - entry) / entry * 100.0
    if action == "long":
        if invalidation_price is not None and price <= invalidation_price:
            return "incorrect", ret, "price at or below invalidation level"
        return ("correct" if ret > 0 else "incorrect"), ret, None
    if action == "short":
        if invalidation_price is not None and price >= invalidation_price:
            return "incorrect", ret, "price at or above invalidation level"
        return ("correct" if ret < 0 else "incorrect"), ret, None
    if action == "watch":
        return ("correct" if abs(ret) <= BAND_PCT else "incorrect"), ret, \
            "watch is correct when price stayed within +/-%.0f%%" % BAND_PCT
    if action == "avoid":
        return ("correct" if ret < BAND_PCT else "incorrect"), ret, \
            "avoid is correct when price did not rise more than %.0f%%" % BAND_PCT
    raise ValueError("unknown action %r" % action)


def grade_one(client: Client, receipt, now=None, force=False, root=None):
    if receipt["grade"] != "pending":
        return receipt
    if not force and not due(receipt, now):
        return receipt
    if not store.verify(receipt):
        raise ValueError("receipt %s fails its integrity hash" % receipt["id"])
    entry = receipt.get("entry_price")
    if not entry:
        return store.update_grade(receipt["id"], {"grade_note": "cannot grade: no entry price was recorded"}, root)
    try:
        price = find_price({"analyze_token": client.call("analyze_token", receipt["symbol"])})
    except RyoError as e:
        return store.update_grade(receipt["id"], {"grade_note": "grading deferred: price call %s (%s)" % (e.status, e.message)}, root)
    if price is None:
        return store.update_grade(receipt["id"], {"grade_note": "grading deferred: price not found in tool output"}, root)
    grade, ret, note = judge(receipt["practice_action"], entry, price, receipt.get("invalidation_price"))
    return store.update_grade(receipt["id"], {
        "grade": grade, "grade_timestamp": now_iso(), "grade_price": price,
        "grade_return_pct": round(ret, 4), "grade_note": note}, root)


def grade_due(client, now=None, force=False, root=None):
    return [grade_one(client, r, now, force, root) for r in store.all_receipts(root) if r["grade"] == "pending"]
