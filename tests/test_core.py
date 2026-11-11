"""Unit tests. FIXTURES BELOW ARE SYNTHETIC TEST DOUBLES, not RYO data, and are never written to data/."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from verity import grade, site, skill, store
from verity.receipt import body_hash, make_receipt
from verity.ryo import Client, RyoError, args_for

SCHEMA = {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}


def fake(tool_data, status_for=None):
    """Fake MCP server transport. tool_data: {name: payload}; status_for: {name: http_status}."""
    def send(payload, session=None):
        m = payload["method"]
        if m == "initialize":
            return 200, json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": {}}), "sess"
        if m == "notifications/initialized":
            return 202, "", None
        if m == "tools/list":
            tools = [{"name": n, "inputSchema": SCHEMA} for n in tool_data]
            return 200, json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": {"tools": tools}}), None
        n = payload["params"]["name"]
        if status_for and n in status_for:
            return status_for[n], "err", None
        body = {"jsonrpc": "2.0", "id": payload["id"], "result": {"content": [{"type": "text", "text": json.dumps(tool_data[n])}]}}
        return 200, "event: message\ndata: %s\n\n" % json.dumps(body), None  # also exercises SSE parsing
    return send


BULL = {"analyze_token": {"price": 100.0, "change_24h": 6.0, "rsi": 25}, "deep_analysis": {"signal": "bullish"}}


class Tests(unittest.TestCase):
    def test_long_receipt_and_grade_correct(self):
        r = make_receipt(Client(transport=fake(BULL)), "btc", 0.0)
        self.assertEqual(r["practice_action"], "long")
        self.assertEqual(r["entry_price"], 100.0)
        self.assertEqual(r["invalidation_price"], 95.0)
        self.assertTrue(all(t["status"] in ("ok", "unavailable") for t in r["tools"]))
        with tempfile.TemporaryDirectory() as d:
            store.save(r, d)
            up = {"analyze_token": {"price": 110.0}, "deep_analysis": {}}
            out = grade.grade_one(Client(transport=fake(up)), store.load(r["id"], d), root=d)
            self.assertEqual(out["grade"], "correct")
            self.assertAlmostEqual(out["grade_return_pct"], 10.0)

    def test_invalidation_breach_is_incorrect(self):
        g, ret, _ = grade.judge("long", 100, 90, 95)
        self.assertEqual(g, "incorrect")
        self.assertEqual(grade.judge("short", 100, 90, 105)[0], "correct")
        self.assertEqual(grade.judge("watch", 100, 101, None)[0], "correct")
        self.assertEqual(grade.judge("avoid", 100, 120, None)[0], "incorrect")

    def test_pending_before_window(self):
        r = make_receipt(Client(transport=fake(BULL)), "BTC", 24.0)
        out = grade.grade_one(Client(transport=fake(BULL)), r)
        self.assertEqual(out["grade"], "pending")

    def test_failures_are_visible_and_degrade_to_watch(self):
        r = make_receipt(Client(transport=fake(BULL, {"deep_analysis": 429, "analyze_token": 503})), "ETH")
        st = {t["name"]: t["status"] for t in r["tools"]}
        self.assertEqual(st["deep_analysis"], "rate_limited")
        self.assertEqual(st["analyze_token"], "unavailable")
        self.assertEqual(r["practice_action"], "watch")
        self.assertLessEqual(r["confidence"], 0.3)
        self.assertTrue(r["raw_evidence"]["deep_analysis"]["unavailable"])

    def test_missing_key_is_unavailable_not_invented(self):
        r = make_receipt(Client(key=""), "SOL")
        self.assertTrue(all(t["status"] == "unavailable" for t in r["tools"]))
        self.assertIsNone(r["entry_price"])
        self.assertEqual(r["practice_action"], "watch")

    def test_tamper_detected_and_append_only(self):
        r = make_receipt(Client(transport=fake(BULL)), "BTC")
        with tempfile.TemporaryDirectory() as d:
            store.save(r, d)
            with self.assertRaises(FileExistsError):
                store.save(r, d)
            t = store.load(r["id"], d); t["thesis"] = "edited"
            self.assertNotEqual(body_hash(t), t["receipt_hash"])
            with open(os.path.join(d, r["id"] + ".json"), "w") as f:
                json.dump(t, f)
            with self.assertRaises(ValueError):
                store.update_grade(r["id"], {"grade": "correct"}, d)

    def test_site_escapes_html_and_builds(self):
        r = make_receipt(Client(transport=fake(BULL)), "BTC")
        r["thesis"] = "<script>alert(1)</script>"
        with tempfile.TemporaryDirectory() as d:
            self.assertNotIn("<script>alert", site.receipt_html(r))
            store.save(r, os.path.join(d, "data")); out = os.path.join(d, "site")
            self.assertEqual(site.build(os.path.join(d, "data"), out), 1)
            self.assertTrue(os.path.exists(os.path.join(out, "index.html")))

    def test_skill_roundtrip(self):
        out = skill.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(len(out["result"]["tools"]), 3)
        err = skill.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "nope", "arguments": {}}})
        self.assertTrue(err["result"]["isError"])

    def test_args_mapping(self):
        self.assertEqual(args_for(SCHEMA, "BTC"), {"symbol": "BTC"})
        with self.assertRaises(RyoError):
            args_for({"properties": {"n": {"type": "integer"}}, "required": ["n"]}, "BTC")


if __name__ == "__main__":
    unittest.main()
