"""Run the pipeline, score it, and save two reports side by side."""
import sys

from agent.reviewer import review
from agent.schema_check import readiness_score
from config import OUTPUT_DIR
from data_generator import generate_sample_data
from etl import extract, transform, load
from report import build_report


def ai_review_text(code_file, det, ai, load_info, df):
    lines = []
    lines.append("=" * 70)
    lines.append("  AI REVIEW REPORT (deterministic rules + Gemini judgment)")
    lines.append("=" * 70)
    lines.append(f"File reviewed:  {code_file}")
    lines.append(f"Model used:    {ai['model_used']}")
    lines.append(f"Rows:           {len(df)} in, {load_info['clean_rows']} clean, {load_info['reject_rows']} rejected")
    lines.append("")
    lines.append(f"{'Area':<14}{'Points':>12}")
    lines.append("-" * 70)
    for name, a in det["areas"].items():
        lines.append(f"{name.title():<14}{a['points']:>6} / {a['max']}")
    lines.append(f"{'Rules total':<14}{det['deterministic_total']:>6} / 90")
    lines.append(f"{'AI judgment':<14}{ai['judgment']:>6} / 10")
    lines.append("-" * 70)
    lines.append(f"FINAL SCORE:  {ai['total']} / 100")
    lines.append(f"VERDICT:      {ai['verdict']}")
    lines.append(f"Reason:       {ai['verdict_reason']}")
    lines.append("")
    lines.append("FAILED CHECKS")
    failed = [(n, d) for n, a in det["areas"].items() for d, ok in a["checks"] if not ok]
    if failed:
        for n, d in failed:
            lines.append(f"  [{n}] {d}")
    else:
        lines.append("  None")
    lines.append("")
    lines.append("AI SUMMARY")
    lines.append(f"  {ai['summary']}")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    code_file = sys.argv[1] if len(sys.argv) > 1 else "etl.py"

    raw_data, truth = generate_sample_data()
    df = transform(extract(raw_data))
    load_info = load(df)

    rule_text = build_report(raw_data, df, load_info, truth)
    det = readiness_score(raw_data, df, load_info)
    ai = review(code_file, det)
    ai_text = ai_review_text(code_file, det, ai, load_info, df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rule_path = OUTPUT_DIR / "rule_report.txt"
    ai_path = OUTPUT_DIR / "ai_review_report.txt"
    rule_path.write_text(rule_text)
    ai_path.write_text(ai_text)

    print(ai_text)
    print()
    print(rule_text)
    print(f"\nSaved:\n  {rule_path}\n  {ai_path}")


if __name__ == "__main__":
    main()
