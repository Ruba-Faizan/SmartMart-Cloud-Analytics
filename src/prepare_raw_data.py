from pathlib import Path
import numpy as np
import pandas as pd


def main():
    raw_dir = Path("data/raw")
    source_xls = raw_dir / "Sample - Superstore.xls"

    if not source_xls.exists():
        raise FileNotFoundError(
            f"'{source_xls}' nahi mili. Pehle 'Sample - Superstore.xls' ko data/raw/ mein rakhein."
        )

    df = pd.read_excel(source_xls)

    # Map original Superstore categories into SmartMart's 4 required categories
    def map_category(row):
        cat = str(row.get("Category", "")).strip()
        sub = str(row.get("Sub-Category", "")).strip()
        if cat == "Technology":
            return "Electronics"
        if cat == "Furniture":
            return "Home Appliances"
        # Split Office Supplies into Clothing and Grocery deterministically
        if sub in {"Art", "Labels", "Envelopes", "Fasteners", "Supplies"}:
            return "Grocery"
        return "Clothing"

    # Assign Store vs Online channel using Ship Mode
    def map_channel(ship_mode):
        mode = str(ship_mode).strip()
        if mode in {"Same Day", "First Class"}:
            return "Online"
        return "Store"

    df["transaction_id"] = df["Order ID"].astype(str)
    df["transaction_date"] = pd.to_datetime(df["Order Date"]).dt.strftime("%Y-%m-%d")
    df["customer_id"] = df["Customer ID"].astype(str)
    df["customer_name"] = df["Customer Name"].astype(str)
    df["product_id"] = df["Product ID"].astype(str)
    df["product_name"] = df["Product Name"].astype(str)
    df["category"] = df.apply(map_category, axis=1)
    df["channel"] = df["Ship Mode"].apply(map_channel)
    df["city"] = df["City"].astype(str)
    df["region"] = df["Region"].astype(str)
    df["quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(1).astype(int)

    # Derive unit_price and unit_cost from Sales and Profit
    sales = pd.to_numeric(df["Sales"], errors="coerce").fillna(0.0)
    profit = pd.to_numeric(df["Profit"], errors="coerce").fillna(0.0)
    qty_safe = df["quantity"].replace(0, 1)

    df["unit_price"] = (sales / qty_safe).round(2)
    df["unit_cost"] = ((sales - profit) / qty_safe).clip(lower=0.01).round(2)
    df["discount_pct"] = pd.to_numeric(df["Discount"], errors="coerce").fillna(0.0).clip(0.0, 0.8)

    cols = [
        "transaction_id",
        "transaction_date",
        "channel",
        "region",
        "city",
        "customer_id",
        "customer_name",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_pct",
    ]
    clean_base = df[cols].copy()

    # Split into Store (Excel) and Online (CSV) files
    store_df = clean_base[clean_base["channel"] == "Store"].copy()
    online_df = clean_base[clean_base["channel"] == "Online"].copy()

    # Create a third export file with intentional realistic data-quality issues
    # (duplicates, missing customer_id, inconsistent casing/spaces, invalid quantity)
    rng = np.random.default_rng(42)
    messy_sample = clean_base.sample(n=min(250, len(clean_base)), random_state=42).copy()

    # Introduce missing customer IDs in ~12% of messy rows
    missing_idx = rng.choice(messy_sample.index, size=max(1, len(messy_sample) // 8), replace=False)
    messy_sample.loc[missing_idx, "customer_id"] = ""

    # Introduce inconsistent casing & extra spaces in category/region
    messy_sample["category"] = messy_sample["category"].apply(
        lambda x: f"  {x.lower()}  " if rng.random() < 0.4 else x
    )
    messy_sample["region"] = messy_sample["region"].apply(
        lambda x: f" {x.upper()} " if rng.random() < 0.3 else x
    )

    # Introduce a few invalid rows (zero/negative quantity) that ETL should reject
    bad_idx = rng.choice(messy_sample.index, size=5, replace=False)
    messy_sample.loc[bad_idx, "quantity"] = 0

    # Append duplicate rows from store_df to test deduplication
    dups = store_df.sample(n=min(30, len(store_df)), random_state=7).copy()
    monthly_export_df = pd.concat([messy_sample, dups], ignore_index=True)

    store_df.to_excel(raw_dir / "smartmart_store_sales.xlsx", index=False)
    online_df.to_csv(raw_dir / "smartmart_online_sales.csv", index=False)
    monthly_export_df.to_csv(raw_dir / "smartmart_monthly_export.csv", index=False)

    print("Raw files generated successfully in data/raw/:")
    print(f" - smartmart_store_sales.xlsx: {len(store_df)} rows")
    print(f" - smartmart_online_sales.csv: {len(online_df)} rows")
    print(f" - smartmart_monthly_export.csv: {len(monthly_export_df)} rows (includes dirty & duplicate test rows)")


if __name__ == "__main__":
    main()