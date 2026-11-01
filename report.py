"""Step 3: build the terminal report (stage scores, failed checks, classification report)."""
from pathlib import Path

from sklearn.metrics import classification_report, confusion_matrix

from config import EXPECTED_COLUMNS, STAGE_WEIGHTS


def status_for(score: float) -> str:
    if score >= 85:
        return "PASS"
    if score >= 60:
        return "NEEDS WORK"
    return "BAD"


def run_checks(raw_data, df, load_info):
    """Each check is (stage, description, passed)."""
    clean_df = load_info["clean_df"]
    return [
        ("extract", "all expected columns present", set(raw_data.keys()) == set(EXPECTED_COLUMNS)),
        ("extract", "at least one row received", len(df) > 0),
        ("extract", "order_id has no blanks", bool(df["order_id"].notna().all())),
        ("load", "clean CSV written", Path(load_info["clean_path"]).exists()),
        ("load", "reject CSV written", Path(load_info["rejects_path"]).exists()),
        ("load", "clean + rejects equals input rows",
         load_info["clean_rows"] + load_info["reject_rows"] == len(df)),
        ("load", "no duplicate order_id in clean output",
         not clean_df["order_id"].duplicated().any()),
    ]


def stage_scores(checks, df, load_info):
    """Score each stage out of 100."""
    results = {}
    for stage in ["extract", "transform", "load"]:
        if stage == "transform":
            # Transform score = share of rows that passed every validation rule
            total = len(df)
            passed = load_info["clean_rows"]
        else:
            stage_checks = [c for c in checks if c[0] == stage]
            total = len(stage_checks)
            passed = sum(1 for c in stage_checks if c[2])

        score = round(100 * passed / total, 1) if total else 0.0
        results[stage] = {"passed": passed, "total": total, "score": score, "status": status_for(score)}
    return results


def build_report(raw_data, df, load_info, truth) -> str:
    checks = run_checks(raw_data, df, load_info)
    scores = stage_scores(checks, df, load_info)
    overall = round(sum(STAGE_WEIGHTS[s] * scores[s]["score"] for s in scores), 1)

    if overall >= 85:
        verdict = "APPROVE"
    elif overall >= 60:
        verdict = "APPROVE WITH CHANGES"
    else:
        verdict = "REJECT"

    # Classification report: validator prediction vs planted truth
    y_pred = (df["issues"] != "").astype(int).tolist()
    cls_report = classification_report(
        truth, y_pred, labels=[0, 1], target_names=["clean", "bad"], zero_division=0
    )
    cm = confusion_matrix(truth, y_pred, labels=[0, 1])

    # Count how often each rule fired
    rule_counts = (
        df.loc[df["issues"] != "", "issues"]
        .str.rstrip(";")
        .str.split(";")
        .explode()
        .value_counts()
    )

    lines = []
    lines.append("=" * 70)
    lines.append("  PIPELINE CODE REVIEW REPORT")
    lines.append("=" * 70)
    lines.append(f"Source:        in-memory dictionary ({len(df)} orders)")
    lines.append(f"Clean output:  {load_info['clean_path']}  ({load_info['clean_rows']} rows)")
    lines.append(f"Rejects:       {load_info['rejects_path']}  ({load_info['reject_rows']} rows)")
    lines.append("")
    lines.append("ETL summary: generate orders -> extract to DataFrame -> validate and clean -> load CSV.")
    lines.append("")

    lines.append("STAGE SCORES")
    lines.append("-" * 70)
    lines.append(f"{'Stage':<12}{'Passed':>10}{'Total':>10}{'Score':>10}   Status")
    for stage, r in scores.items():
        lines.append(f"{stage.title():<12}{r['passed']:>10}{r['total']:>10}{r['score']:>9.1f}%   {r['status']}")
    lines.append("-" * 70)
    lines.append(f"Overall readiness: {overall}/100  (Extract 30%, Transform 30%, Load 40%)")
    lines.append(f"Verdict: {verdict}")
    lines.append("")

    lines.append("FAILED CHECKS")
    failed = [c for c in checks if not c[2]]
    if failed:
        for stage, desc, _ in failed:
            lines.append(f"  [{stage}] {desc}")
    else:
        lines.append("  None")
    lines.append("")

    lines.append("ISSUES BY RULE (rows rejected)")
    if len(rule_counts) == 0:
        lines.append("  None")
    else:
        for rule, n in rule_counts.items():
            lines.append(f"  {rule:<20}{n:>5}")
    lines.append("")

    lines.append("CLASSIFICATION REPORT (validator vs planted problems)")
    lines.append("-" * 70)
    lines.append(cls_report)
    lines.append("Confusion matrix (rows = actual, columns = predicted)")
    lines.append(f"{'':<14}{'pred clean':>12}{'pred bad':>12}")
    lines.append(f"{'actual clean':<14}{cm[0][0]:>12}{cm[0][1]:>12}")
    lines.append(f"{'actual bad':<14}{cm[1][0]:>12}{cm[1][1]:>12}")
    lines.append("=" * 70)

    return "\n".join(lines)
