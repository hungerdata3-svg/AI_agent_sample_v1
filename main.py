"""Run the full pipeline, score it, and get Gemini's review."""
import sys

from agent.reviewer import review
from agent.schema_check import readiness_score
from config import OUTPUT_DIR
from data_generator import generate_sample_data
from etl import extract, transform, load
from report import build_report


def main():
    code_file = sys.argv[1] if len(sys.argv) > 1 else "etl.py"

    raw_data, truth = generate_sample_data()
    df = transform(extract(raw_data))
    load_info = load(df)

    det = readiness_score(raw_data, df, load_info)
    ai = review(code_file, det)

    lines = []
    lines.append("=" * 70)
    lines.append("  PIPELINE READINESS REVIEW")
    lines.append("=" * 70)
    lines.append(f"File reviewed:  {code_file}")
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
    lines.append(f"Reason:       {ai.get('verdict_reason', '')}")
    lines.append("")
    lines.append("FAILED CHECKS")
    failed = [(name, desc) for name, a in det["areas"].items() for desc, ok in a["checks"] if not ok]
    if failed:
        for name, desc in failed:
            lines.append(f"  [{name}] {desc}")
    else:
        lines.append("  None")
    lines.append("")
    lines.append("AI SUMMARY")
    lines.append(f"  {ai['summary']}")
    lines.append("=" * 70)

    readiness_text = "\n".join(lines)
    detail_text = build_report(raw_data, df, load_info, truth)
    full_text = readiness_text + "\n\n" + detail_text

    print(full_text)

    report_path = OUTPUT_DIR / "review_report.txt"
    report_path.write_text(full_text)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
