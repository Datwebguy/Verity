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
