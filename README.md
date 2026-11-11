# Verity

An autonomous agent that produces public, graded practice decisions from live RYO-CHAN research tools.

## Quick start for agents
Read these files in order before writing any code:

1. Prj.md
2. product.md
3. agent-prompt.md
4. resources.md
5. receipt.md

## What to build
A working agent that calls RYO-CHAN tools, writes a practice receipt, grades it later, publishes it publicly, and exposes the same logic as a skill.

## Rules
- Do not use Claude as an author or co-author.
- Do not commit real keys.
- Do not invent RYO data.
- Do not place real trades.
- Make failures visible.

## RYO-CHAN tools used, and why
| Tool | Role in Verity |
|------|----------------|
| `analyze_token` | Required. Quick structured evidence: price, performance, technicals. Also the price source for grading. |
| `deep_analysis` | Required. Comprehensive read on the token: context, risks, derivatives. |
| `market_overview` | Optional context: broad market regime. Cached per run. |
| `monitor_market_sentiment_shift` | Optional context: 7-day sentiment change. Cached per run. |

How the RYO result contract is honoured (builder guide section 4 and 10):
- `status: unavailable` is recorded as a failure, never as zero. `partial` is kept and annotated.
- `data_mode: simulated` is excluded from evidence. Grading only uses `data_mode: live` prices.
- Decisions read structured `data` fields, not summary text. Full responses are stored in `raw_evidence`.
- Only 503 and network errors are retried (backoff with jitter). 429 is recorded as `rate_limited`, not retried.
- The live catalog (`python -m verity tools`) is the source of truth for tool schemas.

## Run it
Python 3.9+, no dependencies.

```bash
cp .env.example .env        # put your RYO_MCP_KEY in .env (never commit it)
python -m verity tools      # list the tools the live RYO-CHAN server offers
python -m verity receipt BTC ETH
python -m verity grade      # grades receipts whose window has elapsed
python -m verity build      # regenerates the public site in docs/
python -m verity serve      # skill server (MCP-style JSON-RPC on :8787)
python -m verity loop --symbols BTC,ETH,SOL --every 3600
python -m unittest discover -s tests
```

Grading rules: `docs/GRADING.md`. Public site: open `docs/index.html` or serve `docs/` with GitHub Pages.
If the key is missing or a tool fails, the receipt records the failure and no data is invented.

## License
MIT
