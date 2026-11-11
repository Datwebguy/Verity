# Receipt

## Format
Every practice receipt produced by Verity must contain the following fields:

- `symbol` — token symbol
- `timestamp` — ISO timestamp when the receipt was created
- `tools` — list of RYO tools called and the status of each (ok / failed / rate_limited / unavailable)
- `evidence_summary` — short text summary of the evidence used
- `thesis` — the agent’s thesis
- `practice_action` — one of: long, short, watch, avoid
- `invalidation` — price level or condition that invalidates the practice action
- `confidence` — number between 0 and 1
- `grade` — pending, correct, or incorrect
- `grade_timestamp` — ISO timestamp when the grade was set (null if pending)
- `raw_evidence` — stored responses from RYO tools (or explicit unavailable markers)

## Rules
- Never invent RYO data.
- If a tool fails, record the failure in `tools` and continue.
- Grade is set only after the defined window and only from real subsequent price movement.
- All receipts are public once written.
