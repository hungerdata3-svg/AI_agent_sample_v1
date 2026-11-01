"""Deterministic readiness score out of 100. No AI involved."""
import pandas as pd
import yaml

from config import EXPECTED_COLUMNS


def load_spec(path="specs/orders_target.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def score_extract(raw_data: dict, df: pd.DataFrame) -> dict:
    """Extract = 25 points, split into four equal checks."""
    checks = [
        ("source columns match expected list", set(raw_data.keys()) == set(EXPECTED_COLUMNS)),
        ("at least one row received", len(df) > 0),
        ("order_id has no blanks", bool(df["order_id"].notna().all())),
        ("granularity: one row per order_id (no duplicates)", not df["order_id"].duplicated().any()),
    ]
    passed = sum(1 for _, ok in checks if ok)
    return {"points": round(25 * passed / len(checks), 1), "max": 25, "checks": checks}


def score_schema(df: pd.DataFrame, spec: dict) -> dict:
    """Schema vs destination = 25 points. Compares source columns to the target spec."""
    columns = spec["columns"]
    checks = []
    for name, rule in columns.items():
        present = name in df.columns
        checks.append((f"column '{name}' exists in source", present))
        if present and rule.get("required"):
            checks.append((f"column '{name}' has no nulls", bool(df[name].notna().all())))
    checks.append(("primary key declared in spec", spec.get("primary_key") in columns))
    passed = sum(1 for _, ok in checks if ok)
    return {"points": round(25 * passed / len(checks), 1), "max": 25, "checks": checks}


def score_transform(df: pd.DataFrame) -> dict:
    """Transform = 25 points. Counts only validity failures.

    Completeness (missing_customer) is scored under schema.
    Granularity (duplicate_id) is scored under extract.
    """
    owned_elsewhere = ("missing_customer;", "duplicate_id;")
    validity = df["issues"]
    for tag in owned_elsewhere:
        validity = validity.str.replace(tag, "", regex=False)

    valid_rows = int((validity == "").sum())
    total = len(df)
    share = valid_rows / total if total else 0.0
    return {
        "points": round(25 * share, 1),
        "max": 25,
        "checks": [(f"{valid_rows} of {total} rows pass validity rules", share == 1.0)],
    }

def score_load(load_info: dict, df: pd.DataFrame) -> dict:
    """Load = 25 points. Reconciliation and safety of the write."""
    clean_df = load_info["clean_df"]
    checks = [
        ("clean + rejects equals input rows",
         load_info["clean_rows"] + load_info["reject_rows"] == len(df)),
        ("no duplicate order_id in clean output", not clean_df["order_id"].duplicated().any()),
        ("clean CSV written", load_info["clean_path"].exists()),
        ("reject CSV written", load_info["rejects_path"].exists()),
    ]
    passed = sum(1 for _, ok in checks if ok)
    return {"points": round(25 * passed / len(checks), 1), "max": 25, "checks": checks}


def readiness_score(raw_data, df, load_info, spec=None) -> dict:
    """Combine the four areas into a score out of 90 (the model adds up to 10)."""
    spec = spec or load_spec()
    areas = {
        "extract": score_extract(raw_data, df),
        "schema": score_schema(df, spec),
        "transform": score_transform(df),
        "load": score_load(load_info, df),
    }
    total = round(sum(a["points"] for a in areas.values()), 1)
    return {"areas": areas, "deterministic_total": total, "max": 100}
