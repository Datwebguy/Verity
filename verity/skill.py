"""Verity as a callable skill: a small MCP-style JSON-RPC server (POST /) exposing the same logic.

Tools: verity_receipt, verity_grade, verity_scoreboard. Same code path as the CLI/agent loop.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import grade as grading
from . import site, store
from .config import grade_hours
from .receipt import make_receipt
from .ryo import Client

TOOLS = [
    {"name": "verity_receipt",
     "description": "Research a token with live RYO-CHAN tools and publish a structured practice receipt (practice only, no orders).",
     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
    {"name": "verity_grade",
     "description": "Grade a pending receipt against real later price movement once its window has elapsed (or force=true).",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "force": {"type": "boolean"}}, "required": ["id"]}},
    {"name": "verity_scoreboard",
     "description": "Hit rate, pending count and 'always long' baseline across all receipts.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def call(name, args, client=None):
    client = client or Client()
    if name == "verity_receipt":
        r = make_receipt(client, args["symbol"], grade_hours())
        store.save(r)
        return r
    if name == "verity_grade":
        return grading.grade_one(client, store.load(args["id"]), force=bool(args.get("force")))
    if name == "verity_scoreboard":
        return site.scoreboard(store.all_receipts())
    raise KeyError("unknown tool %r" % name)


def handle(msg, client=None):
    mid, method = msg.get("id"), msg.get("method")
    try:
        if method == "initialize":
            res = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                   "serverInfo": {"name": "verity", "version": "0.1.0"}}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            p = msg.get("params", {})
            out = call(p["name"], p.get("arguments", {}), client)
            res = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]}
        elif method and method.startswith("notifications/"):
            return None
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}
        return {"jsonrpc": "2.0", "id": mid, "result": res}
    except Exception as ex:  # failures are visible to the caller, never swallowed
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "isError": True, "content": [{"type": "text", "text": "%s: %s" % (type(ex).__name__, ex)}]}}


class _H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"name": "verity", "status": "ok", "tools": [t["name"] for t in TOOLS]})

    def do_POST(self):
        try:
            msg = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except ValueError:
            return self._send(400, {"error": "invalid JSON"})
        out = handle(msg)
        if out is None:
            self.send_response(202); self.end_headers(); return
        self._send(200, out)

    def log_message(self, *a):
        pass


def serve(host="127.0.0.1", port=8787):
    print("Verity skill listening on http://%s:%d (POST JSON-RPC)" % (host, port))
    HTTPServer((host, port), _H).serve_forever()
