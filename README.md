cat > README.md << 'EOF'
# AI Pipeline Code Reviewer

An AI-assisted readiness checker for data pipelines. Point it at an ETL script and it returns a 100-point score, a verdict, the failed checks, and a review from Gemini.

The scoring is deterministic: code computes 90 of the 100 points, and the model adds up to 10 points of judgment. Only the wording of the AI summary varies between runs. The numbers and the verdict stay the same.

## What it checks

| Area | Points | Checks |
|---|---|---|
| Extract | 25 | Expected columns, rows received, no blank keys, one row per `order_id` |
| Schema | 25 | Target columns exist in the source, required columns have no nulls, primary key declared |
| Transform | 25 | Rows pass validity rules: amounts above zero, valid status values, parseable dates |
| Load | 25 | Row counts reconcile, no duplicate keys in the clean output, both CSVs written |

Each problem is scored in exactly one area, so a single bad row is never penalized twice.

## Verdict rules

- **APPROVE:** score of 85 or higher, with no critical failure
- **APPROVE WITH CHANGES:** score of 60 to 84, or any critical failure
- **REJECT:** score below 60

Critical checks (duplicate keys, reconciliation) cap the verdict at APPROVE WITH CHANGES even when the score is high. A clean-looking score can still hide a dangerous write.

## Project structure
<img width="809" height="463" alt="Screenshot 2026-11-05 at 5 03 50 PM" src="https://github.com/user-attachments/assets/61bb0e12-7a19-4713-9478-242e64efc933" />
