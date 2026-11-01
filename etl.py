"""Step 2: Extract, Transform, Load."""
import pandas as pd

from config import OUTPUT_DIR, VALID_STATUSES


def extract(raw_data: dict) -> pd.DataFrame:
    """EXTRACT: read the raw dictionary into a DataFrame."""
    return pd.DataFrame(raw_data)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """TRANSFORM: clean the types and tag each row with the rules it breaks."""
    df = df.copy()

    # Clean types
    df["status"] = df["status"].astype(str).str.strip().str.upper()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["order_date_parsed"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")

    # Validation rules (True = the row breaks this rule)
    rules = {
        "missing_customer": df["customer_id"].isna() | (df["customer_id"].astype(str).str.strip() == ""),
        "negative_amount": df["amount"].isna() | (df["amount"] <= 0),
        "bad_status": ~df["status"].isin(VALID_STATUSES),
        "bad_date": df["order_date_parsed"].isna(),
        "duplicate_id": df["order_id"].duplicated(keep="first"),
    }

    # Record every rule each row breaks, e.g. "negative_amount;bad_status;"
    df["issues"] = ""
    for name, mask in rules.items():
        df.loc[mask, "issues"] = df.loc[mask, "issues"] + name + ";"

    return df


def load(df: pd.DataFrame) -> dict:
    """LOAD: write clean rows and rejected rows to two CSV files on the Desktop."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    clean_df = df[df["issues"] == ""].drop(columns=["order_date_parsed", "issues"])
    rejects_df = df[df["issues"] != ""].drop(columns=["order_date_parsed"])

    clean_path = OUTPUT_DIR / "orders_clean.csv"
    rejects_path = OUTPUT_DIR / "orders_rejects.csv"
    clean_df.to_csv(clean_path, index=False)
    rejects_df.to_csv(rejects_path, index=False)

    return {
        "clean_path": clean_path,
        "rejects_path": rejects_path,
        "clean_rows": len(clean_df),
        "reject_rows": len(rejects_df),
        "clean_df": clean_df,
    }
