import pandas as pd
from app import compute_filtered_kpis
from src.analytics_sql import verify_sql_kpis
from src.etl_pipeline import clean_sales_data, run_pipeline


def test_data_validation():
    sample_dirty = pd.DataFrame(
        [
            {
                "transaction_id": "TXN-1",
                "transaction_date": "2026-01-10",
                "channel": " online ",
                "region": " east ",
                "city": "new york",
                "customer_id": "",
                "customer_name": "",
                "product_id": "PRD-1",
                "product_name": "Laptop",
                "category": "  electronics ",
                "quantity": 2,
                "unit_price": 500.0,
                "unit_cost": 400.0,
                "discount_pct": 0.10,
            },
            # Duplicate line item (should be removed)
            {
                "transaction_id": "TXN-1",
                "transaction_date": "2026-01-10",
                "channel": "Online",
                "region": "East",
                "city": "New York",
                "customer_id": "",
                "customer_name": "",
                "product_id": "PRD-1",
                "product_name": "Laptop",
                "category": "Electronics",
                "quantity": 2,
                "unit_price": 500.0,
                "unit_cost": 400.0,
                "discount_pct": 0.10,
            },
            # Invalid zero quantity (should be dropped)
            {
                "transaction_id": "TXN-2",
                "transaction_date": "2026-01-11",
                "channel": "Store",
                "region": "West",
                "city": "Seattle",
                "customer_id": "CUST-9",
                "customer_name": "Sara",
                "product_id": "PRD-2",
                "product_name": "Blender",
                "category": "Home Appliances",
                "quantity": 0,
                "unit_price": 100.0,
                "unit_cost": 70.0,
                "discount_pct": 0.0,
            },
        ]
    )

    cleaned, stats = clean_sales_data(sample_dirty)
    assert len(cleaned) == 1, f"Expected 1 clean row, got {len(cleaned)}"
    assert cleaned.loc[0, "customer_id"] == "CUST-UNKNOWN"
    assert cleaned.loc[0, "category"] == "Electronics"
    assert cleaned.loc[0, "channel"] == "Online"
    assert cleaned.loc[0, "net_amount"] == 900.0
    assert cleaned.loc[0, "profit"] == 100.0
    assert stats["dropped_duplicates"] == 1
    assert stats["dropped_invalid_numeric_rows"] == 1
    print("[PASS] Data validation, deduplication, and financial formula tests passed.")


def test_kpi_and_sql_reconciliation():
    clean_df, _ = run_pipeline()
    checks = verify_sql_kpis(clean_df)
    assert checks["revenue_match"], f"Revenue mismatch: {checks}"
    assert checks["profit_match"], f"Profit mismatch: {checks}"
    assert checks["orders_match"], f"Orders mismatch: {checks}"
    assert checks["aov_match"], f"AOV mismatch: {checks}"
    print("[PASS] SQL Star Schema views match Pandas KPI calculations 100%.")


def test_empty_filter_behavior():
    empty_df = pd.DataFrame(
        columns=["transaction_id", "customer_id", "net_amount", "profit"]
    )
    kpis = compute_filtered_kpis(empty_df)
    assert kpis["revenue"] == 0.0
    assert kpis["orders"] == 0
    assert kpis["aov"] == 0.0
    assert kpis["repeat_rate_pct"] == 0.0
    print("[PASS] Empty filter edge-case handled cleanly without ZeroDivisionError.")


if __name__ == "__main__":
    test_data_validation()
    test_kpi_and_sql_reconciliation()
    test_empty_filter_behavior()
    print("\nAll SmartMart automated verification checks PASSED!")