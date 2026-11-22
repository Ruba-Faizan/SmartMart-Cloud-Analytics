import glob
from pathlib import Path
import numpy as np
import pandas as pd


def load_raw_files(raw_dir: str = "data/raw") -> pd.DataFrame:
    """Load SmartMart raw CSV and Excel files from raw_dir into a single DataFrame."""
    frames = []
    for path in sorted(glob.glob(f"{raw_dir}/*")):
        p = Path(path)
        if p.name.lower() == "sample - superstore.xls":
            continue

        if p.suffix.lower() == ".csv":
            df = pd.read_csv(
                p,
                dtype={"transaction_id": str, "customer_id": str, "product_id": str},
                keep_default_na=False,
            )
        elif p.suffix.lower() in {".xlsx", ".xls"}:
            df = pd.read_excel(
                p,
                dtype={"transaction_id": str, "customer_id": str, "product_id": str},
                keep_default_na=False,
            )
        else:
            continue

        df["source_file"] = p.name
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"Koi SmartMart raw CSV ya Excel file '{raw_dir}' mein nahi mili.")

    return pd.concat(frames, ignore_index=True)


def clean_sales_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Validate fields, standardize values, remove duplicates, and return clean data + audit stats."""
    stats = {"raw_rows": len(df)}
    out = df.copy()

    # 1. Trim whitespace and normalize missing-like string tokens
    text_cols = [
        "transaction_id",
        "customer_id",
        "customer_name",
        "product_id",
        "product_name",
        "channel",
        "category",
        "city",
        "region",
    ]
    for col in text_cols:
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()
            out.loc[out[col].isin(["", "nan", "NaN", "None", "NULL", "null"]), col] = np.nan

    # 2. Standardize channel, category, city, and region casing
    if "channel" in out.columns:
        out["channel"] = out["channel"].str.title().replace({"E-Commerce": "Online", "Web": "Online"})
    if "category" in out.columns:
        out["category"] = out["category"].str.title()
    for col in ["city", "region"]:
        if col in out.columns:
            out[col] = out[col].str.title()

    # 3. Parse dates and drop rows with missing core identifiers or invalid dates
    out["transaction_date"] = pd.to_datetime(out["transaction_date"], errors="coerce")
    before_req = len(out)
    out = out.dropna(subset=["transaction_id", "product_id", "transaction_date"])
    stats["dropped_missing_keys_or_date"] = before_req - len(out)

    # 4. Handle missing customer_id explicitly instead of dropping valid sales
    missing_cust_count = int(out["customer_id"].isna().sum())
    out["customer_id"] = out["customer_id"].fillna("CUST-UNKNOWN")
    out["customer_name"] = out["customer_name"].fillna("Unknown Customer")
    stats["imputed_missing_customers"] = missing_cust_count

    # 5. Numeric validation: positive quantity, valid price/cost, discount clamped to [0, 0.80]
    for col in ["quantity", "unit_price", "unit_cost", "discount_pct"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["discount_pct"] = out["discount_pct"].fillna(0.0).clip(0.0, 0.80)
    before_num = len(out)
    out = out.dropna(subset=["quantity", "unit_price", "unit_cost"])
    out = out[(out["quantity"] > 0) & (out["unit_price"] > 0) & (out["unit_cost"] >= 0)]
    out["quantity"] = out["quantity"].astype(int)
    stats["dropped_invalid_numeric_rows"] = before_num - len(out)

    # 6. Remove duplicate line items (keep latest record by transaction_date)
    before_dedup = len(out)
    out = out.sort_values("transaction_date").drop_duplicates(
        subset=["transaction_id", "product_id"], keep="last"
    )
    stats["dropped_duplicates"] = before_dedup - len(out)

    # 7. Compute financial metrics consistently
    out["gross_amount"] = (out["quantity"] * out["unit_price"]).round(2)
    out["net_amount"] = (out["gross_amount"] * (1.0 - out["discount_pct"])).round(2)
    out["total_cost"] = (out["quantity"] * out["unit_cost"]).round(2)
    out["profit"] = (out["net_amount"] - out["total_cost"]).round(2)

    out["transaction_date"] = out["transaction_date"].dt.strftime("%Y-%m-%d")
    stats["clean_rows"] = len(out)

    return out.reset_index(drop=True), stats


def run_pipeline(
    raw_dir: str = "data/raw",
    output_path: str = "data/processed/smartmart_clean_sales.csv",
) -> tuple[pd.DataFrame, dict]:
    raw_df = load_raw_files(raw_dir)
    clean_df, stats = clean_sales_data(raw_df)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(out_file, index=False)
    return clean_df, stats


if __name__ == "__main__":
    clean_df, stats = run_pipeline()
    print("ETL Pipeline Complete! Audit Summary:")
    for k, v in stats.items():
        print(f" - {k}: {v}")
    print(f"Saved clean dataset to: data/processed/smartmart_clean_sales.csv")