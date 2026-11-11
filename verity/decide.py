"""Rule-based practice decision. Deterministic, no LLM. Only uses values actually present in tool output."""
PRICE_KEYS = {"price", "price_usd", "priceusd", "current_price", "currentprice", "last_price", "lastprice", "usd_price"}
CHANGE_KEYS = {"change_24h", "price_change_24h", "percent_change_24h", "change24h", "pricechange24h", "price_change_percentage_24h", "change_pct_24h"}
RSI_KEYS = {"rsi", "rsi_14", "rsi14"}
TEXT_KEYS = {"signal", "recommendation", "verdict", "trend", "sentiment", "rating", "bias"}
RISK_KEYS = {"risk", "risk_level", "risklevel", "verdict", "safety", "rating"}
RISK_BAD = {"high", "critical", "unsafe", "danger", "dangerous", "scam", "avoid"}
BULL = ("bullish", "buy", "uptrend", "long")
BEAR = ("bearish", "sell", "downtrend", "short")
STOP_PCT = 5.0


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k).lower(), v
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").replace("%", "").replace("$", ""))
        except ValueError:
            return None
    return None


def first_number(obj, keys):
    for k, v in walk(obj):
        if k in keys and _num(v) is not None:
            return _num(v)
    return None


def find_price(evidence):
    """First price found across the evidence dicts (analyze_token first)."""
    for name in ("analyze_token", "deep_analysis"):
        if name in evidence:
            p = first_number(evidence[name], PRICE_KEYS)
            if p and p > 0:
                return p
    return None


def _safety_flag(obj):
    for k, v in walk(obj):
        if k in ("honeypot", "is_honeypot") and v is True:
            return True
        if k in RISK_KEYS and isinstance(v, str) and v.strip().lower() in RISK_BAD:
            return True
    return False


def decide(evidence):
    """evidence: {tool_name: parsed response} for tools that returned ok."""
    signals, notes, score = {}, [], 0
    price = find_price(evidence)
    if price is not None:
        signals["price"] = price
    for name, data in evidence.items():
        ch = first_number(data, CHANGE_KEYS)
        if ch is not None and "change_24h" not in signals:
            signals["change_24h"] = ch
            if ch > 3:
                score += 1; notes.append("24h change %+.2f%% (momentum up)" % ch)
            elif ch < -3:
                score -= 1; notes.append("24h change %+.2f%% (momentum down)" % ch)
            else:
                notes.append("24h change %+.2f%% (flat)" % ch)
        rsi = first_number(data, RSI_KEYS)
        if rsi is not None and "rsi" not in signals:
            signals["rsi"] = rsi
            if rsi > 70:
                score -= 1; notes.append("RSI %.0f (overbought)" % rsi)
            elif rsi < 30:
                score += 1; notes.append("RSI %.0f (oversold)" % rsi)
            else:
                notes.append("RSI %.0f (neutral)" % rsi)
        for k, v in walk(data):
            if k in TEXT_KEYS and isinstance(v, str):
                low = v.lower()
                if any(w in low for w in BULL) and not any(w in low for w in BEAR):
                    score += 1; notes.append("%s says %r (bullish)" % (name, v[:40])); break
                if any(w in low for w in BEAR) and not any(w in low for w in BULL):
                    score -= 1; notes.append("%s says %r (bearish)" % (name, v[:40])); break
    unsafe = "check_safety" in evidence and _safety_flag(evidence["check_safety"])
    if unsafe:
        notes.append("check_safety flagged elevated risk")
    signals["score"] = score

    required_ok = "analyze_token" in evidence and "deep_analysis" in evidence
    if unsafe:
        action, conf = "avoid", 0.6
    elif not required_ok or price is None or not notes:
        action, conf = "watch", 0.2
    elif score >= 2:
        action, conf = "long", min(0.8, 0.4 + 0.1 * score)
    elif score <= -2:
        action, conf = "short", min(0.8, 0.4 + 0.1 * -score)
    else:
        action, conf = "watch", 0.35
    if not required_ok:
        conf = min(conf, 0.3)

    inv_price = None
    if price is not None and action == "long":
        inv_price = round(price * (1 - STOP_PCT / 100), 8)
    elif price is not None and action == "short":
        inv_price = round(price * (1 + STOP_PCT / 100), 8)
    if inv_price is not None:
        invalidation = "%s if price %s %s" % (
            "Wrong" , "closes below" if action == "long" else "closes above", inv_price)
    elif action == "avoid":
        invalidation = "Re-evaluate if check_safety stops flagging risk."
    else:
        invalidation = "No directional call; re-evaluate on the next receipt."

    summary = "; ".join(notes) if notes else "No parseable signals in tool output."
    if price is None:
        summary += " Price not found in tool output, so no entry price is recorded."
    thesis = {
        "long": "Evidence leans bullish (score %+d); practice long." % score,
        "short": "Evidence leans bearish (score %+d); practice short." % score,
        "avoid": "Safety check flagged elevated risk; practice avoid.",
        "watch": "Evidence is thin, mixed or incomplete (score %+d); practice watch." % score,
    }[action]
    return {"action": action, "confidence": round(conf, 2), "thesis": thesis,
            "invalidation": invalidation, "invalidation_price": inv_price,
            "entry_price": price, "evidence_summary": summary, "signals": signals}
