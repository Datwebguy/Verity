"""Minimal MCP-over-HTTP client for RYO-CHAN.

Every failure is raised as RyoError carrying one of the receipt statuses:
ok / failed / rate_limited / unavailable. Nothing is ever fabricated.
"""
import json
import os
import urllib.error
import urllib.request

DEFAULT_URL = "https://app-ryochan.com/api/mcp"


class RyoError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _parse_body(text):
    text = text.strip()
    if text.startswith(("{", "[")):
        return json.loads(text)
    last = None
    for line in text.splitlines():  # Server-Sent Events framing
        if line.startswith("data:") and line[5:].strip():
            last = line[5:].strip()
    if last is None:
        raise ValueError("empty or unparseable response")
    return json.loads(last)


def http_transport(url, key, timeout):
    def send(payload, session_id=None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + key,
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        req = urllib.request.Request(url, json.dumps(payload).encode(), headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace"), r.headers.get("Mcp-Session-Id")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RyoError("unavailable", "network error: %s" % getattr(e, "reason", e))
    return send


class Client:
    def __init__(self, key=None, url=None, timeout=30, transport=None):
        self.key = key if key is not None else os.environ.get("RYO_MCP_KEY", "")
        self.url = url or os.environ.get("RYO_MCP_URL", DEFAULT_URL)
        self.timeout = timeout
        self._send = transport
        self._session = None
        self._id = 0
        self._ready = False
        self._tools = None

    def _transport(self):
        if self._send:
            return self._send
        if not self.key:
            raise RyoError("unavailable", "RYO_MCP_KEY is not set")
        return http_transport(self.url, self.key, self.timeout)

    def _rpc(self, method, params=None, notify=False):
        send = self._transport()
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notify:
            self._id += 1
            payload["id"] = self._id
        status, text, sid = send(payload, self._session)
        if sid:
            self._session = sid
        if status == 429:
            raise RyoError("rate_limited", "HTTP 429 rate limited")
        if status in (401, 403):
            raise RyoError("unavailable", "HTTP %d: credential missing or rejected" % status)
        if status >= 500:
            raise RyoError("unavailable", "HTTP %d server error" % status)
        if notify:
            return None
        if status >= 400:
            raise RyoError("failed", "HTTP %d: %s" % (status, text[:200]))
        try:
            msg = _parse_body(text)
        except ValueError as e:
            raise RyoError("failed", "bad response: %s" % e)
        if isinstance(msg, dict) and "error" in msg:
            m = str(msg["error"].get("message", msg["error"]) if isinstance(msg["error"], dict) else msg["error"])
            low = m.lower()
            raise RyoError("rate_limited" if "rate" in low and "limit" in low else "failed", m[:300])
        return msg.get("result")

    def _ensure(self):
        if self._ready:
            return
        self._rpc("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "verity", "version": "0.1.0"}})
        self._rpc("notifications/initialized", notify=True)
        self._ready = True

    def tools(self):
        """{tool_name: tool_definition} as reported by the live server."""
        if self._tools is None:
            self._ensure()
            res = self._rpc("tools/list") or {}
            self._tools = {t["name"]: t for t in res.get("tools", [])}
        return self._tools

    def call(self, name, symbol):
        """Call a tool for a token symbol; arguments are derived from the tool's own input schema."""
        tools = self.tools()
        if name not in tools:
            raise RyoError("unavailable", "tool %r not offered by server (offered: %s)" % (name, ", ".join(sorted(tools)) or "none"))
        args = args_for(tools[name].get("inputSchema"), symbol)
        res = self._rpc("tools/call", {"name": name, "arguments": args}) or {}
        parts = [c.get("text", "") for c in res.get("content", []) if c.get("type") == "text"]
        if res.get("isError"):
            raise RyoError("failed", (" ".join(parts) or "tool reported an error")[:300])
        if res.get("structuredContent") is not None:
            return res["structuredContent"]
        joined = "\n".join(parts)
        try:
            return json.loads(joined)
        except ValueError:
            return {"text": joined}


def args_for(schema, symbol):
    schema = schema or {}
    props = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []
    for k in ("symbol", "token", "ticker", "name", "asset", "query", "address"):
        if k in props:
            return {k: symbol}
    for k in required:
        if (props.get(k) or {}).get("type") == "string":
            return {k: symbol}
    if required:
        raise RyoError("failed", "cannot map a token symbol onto required arguments: %s" % ", ".join(required))
    return {}
