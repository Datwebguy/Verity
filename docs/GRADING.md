# Grading rules

A receipt is graded only after its window (`grade_window_hours`, default 24h) has elapsed, and only
from a real later price returned by the live RYO-CHAN `analyze_token` tool. If that call fails, or
no price can be found in its output, the receipt stays `pending` and `grade_note` says why.

Return = (grade_price - entry_price) / entry_price.

| Action | Correct when |
|--------|--------------|
| long   | return > 0 and grade price is above `invalidation_price` |
| short  | return < 0 and grade price is below `invalidation_price` |
| watch  | price stayed within +/-3% (a no-call was justified) |
| avoid  | price did not rise more than 3% |

Limitations (stated openly):
- Grading uses the price at grade time only, not the path, so an intra-window invalidation touch that
  later recovered is not detected.
- The +/-3% band and the 5% invalidation distance are fixed constants in `verity/grade.py` and `verity/decide.py`.
- `--force` grades immediately and exists for demos; forced grades are real prices but not a full window.

Integrity: each receipt stores a SHA-256 of its decision body (everything except the grade fields).
Receipts are append-only; only grade fields can change, and grading refuses a receipt whose hash no longer matches.
