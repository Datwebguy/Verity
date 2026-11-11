"""Build a practice receipt from live RYO-CHAN tool calls."""
import hashlib
import json
from datetime import datetime, timezone

from .decide import decide
from .ryo import Client, RyoError

REQUIRED = ("analyze_token", "deep_analysis")
OPTIONAL = ("market_overview", "monitor_market_sentiment_shift")
GRADE_FIELDS = ("grade", "grade_timestamp", "grade_price", "grade_return_pct", "grade_note")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def body_hash(receipt):
    body = {k: v for k, v in receipt.items() if k not in GRADE_FIELDS and k != "receipt_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_receipt(client: Client, symbol, grade_hours=24.0):
    symbol = symbol.strip().upper()
    tools, raw, ok_evidence = [], {}, {}
    for name in REQUIRED + OPTIONAL:
        try:
            env = client.call(name, symbol)
            detail = None
            if env.get("status") == "partial":
                detail = "partial: " + "; ".join(env.get("warnings") or ["incomplete evidence sections"])[:200]
            tools.append({"name": name, "status": "ok", "detail": detail, "data_mode": env.get("data_mode")})
            raw[name] = env
            ok_evidence[name] = env.get("data", {})
        except RyoError as e:
            tools.append({"name": name, "status": e.status, "detail": e.message})
            raw[name] = {"unavailable": True, "status": e.status, "reason": e.message}
    d = decide(ok_evidence)
    r = {
        "symbol": symbol,
        "timestamp": now_iso(),
        "tools": tools,
        "evidence_summary": d["evidence_summary"],
        "thesis": d["thesis"],
        "practice_action": d["action"],
        "invalidation": d["invalidation"],
        "invalidation_price": d["invalidation_price"],
        "confidence": d["confidence"],
        "entry_price": d["entry_price"],
        "grade_window_hours": grade_hours,
        "grade": "pending",
        "grade_timestamp": None,
        "grade_price": None,
        "grade_return_pct": None,
        "grade_note": None,
        "raw_evidence": raw,
    }
    r["id"] = "%s-%s" % (r["timestamp"].replace("-", "").replace(":", "").replace("+0000", "Z").replace("+00:00", "Z"), symbol)
    r["receipt_hash"] = body_hash(r)
    return r
