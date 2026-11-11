# Agent Prompt — Verity

You are building Verity.

Read every markdown file in this repository before you write any code.

## Product
Verity is an autonomous agent that:
- Calls multiple RYO-CHAN research tools on a token
- Produces a structured practice receipt
- Grades that receipt later against real price movement
- Publishes the receipt and grade on a public page
- Exposes the same logic as a callable skill

## Hard rules
- Do not use Claude as an author or co-author in any file, commit message, comment, or generated text.
- Do not call Claude.
- Do not commit real API keys.
- Do not invent RYO responses.
- Do not place real trades.
- If a RYO tool fails or is rate-limited, record the failure in the receipt and continue with available data.
- Prefer a complete working loop over partial features.

## RYO tools to use
Required for every receipt:
- analyze_token
- deep_analysis

Use additional tools when relevant:
- compare_tokens
- scan_market
- market_overview
- monitor_market_sentiment_shift

MCP endpoint: https://app-ryochan.com/api/mcp
Builder guide: https://ryobuild.com/mcp-builder-guide.pdf

## Build order
1. Agent that calls RYO tools and writes a receipt.
2. Grading function.
3. Persistence for receipts.
4. Public page that lists receipts.
5. Skill endpoint that returns a receipt for a given token.
6. Clear handling of missing keys and tool failures.

## Success criteria
A person can open the public page, see a receipt produced by the agent, read the evidence and practice decision, and later see a grade. The same receipt logic is callable as a skill.
