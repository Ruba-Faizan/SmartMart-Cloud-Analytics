import sqlite3
import pandas as pd


def build_star_schema(clean_df: pd.DataFrame) -> sqlite3.Connection:
    """Load clean_df into an in-memory SQLite Star Schema (fact_sales + 3 dim tables) and SQL views."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    df = clean_df.copy()

    # Ensure date parsing
    dt = pd.to_datetime(df["transaction_date"])
    df["date_key"] = dt.dt.strftime("%Y%m%d").astype(int)

    # 1. dim_date
    dim_date = pd.DataFrame(
        {
            "date_key": df["date_key"],
            "full_date": dt.dt.strftime("%Y-%m-%d"),
            "year": dt.dt.year,
            "quarter": "Q" + dt.dt.quarter.astype(str),
            "month": dt.dt.month,
            "month_name": dt.dt.strftime("%b"),
            "year_month": dt.dt.strftime("%Y-%m"),
            "day_of_week": dt.dt.day_name(),
        }
    ).drop_duplicates(subset=["date_key"]).sort_values("date_key")

    # 2. dim_customer
    cust_agg = (
        df.groupby(["customer_id", "customer_name"], as_index=False)
        .agg(
            first_order_date=("transaction_date", "min"),
            last_order_date=("transaction_date", "max"),
            total_orders=("transaction_id", "nunique"),
            lifetime_spend=("net_amount", "sum"),
        )
    )
    cust_agg["lifetime_spend"] = cust_agg["lifetime_spend"].round(2)

    def classify_customer(row):
        if row["customer_id"] == "CUST-UNKNOWN":
            return "Guest / Unknown"
        if row["total_orders"] == 1:
            return "New / One-Time"
        if row["lifetime_spend"] >= 2000:
            return "VIP Repeat"
        return "Repeat Buyer"

    cust_agg["customer_segment"] = cust_agg.apply(classify_customer, axis=1)
    dim_customer = cust_agg.drop_duplicates(subset=["customer_id"])

    # 3. dim_product
    dim_product = (
        df[["product_id", "product_name", "category", "unit_price", "unit_cost"]]
        .drop_duplicates(subset=["product_id"])
        .copy()
    )

    # 4. fact_sales
    fact_sales = df[
        [
            "transaction_id",
            "date_key",
            "transaction_date",
            "customer_id",
            "product_id",
            "channel",
            "region",
            "city",
            "quantity",
            "discount_pct",
            "gross_amount",
            "net_amount",
            "total_cost",
            "profit",
        ]
    ].copy()

    # Write tables to SQLite
    dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)
    dim_customer.to_sql("dim_customer", conn, if_exists="replace", index=False)
    dim_product.to_sql("dim_product", conn, if_exists="replace", index=False)
    fact_sales.to_sql("fact_sales", conn, if_exists="replace", index=False)

    # Create analytical SQL Views
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE VIEW vw_kpis AS
        SELECT
            ROUND(COALESCE(SUM(net_amount), 0), 2) AS total_revenue,
            ROUND(COALESCE(SUM(profit), 0), 2) AS total_profit,
            COUNT(DISTINCT transaction_id) AS total_orders,
            COALESCE(SUM(quantity), 0) AS total_units_sold,
            ROUND(
                COALESCE(SUM(net_amount), 0) * 1.0 / NULLIF(COUNT(DISTINCT transaction_id), 0),
                2
            ) AS avg_order_value,
            ROUND(
                COALESCE(SUM(profit), 0) * 100.0 / NULLIF(SUM(net_amount), 0),
                2
            ) AS profit_margin_pct
        FROM fact_sales;

        CREATE VIEW vw_category_performance AS
        SELECT
            p.category,
            COUNT(DISTINCT f.transaction_id) AS orders,
            SUM(f.quantity) AS units_sold,
            ROUND(SUM(f.net_amount), 2) AS revenue,
            ROUND(SUM(f.profit), 2) AS profit,
            ROUND(SUM(f.profit) * 100.0 / NULLIF(SUM(f.net_amount), 0), 2) AS margin_pct
        FROM fact_sales f
        JOIN dim_product p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY revenue DESC;

        CREATE VIEW vw_regional_performance AS
        SELECT
            f.region,
            f.city,
            f.channel,
            COUNT(DISTINCT f.transaction_id) AS orders,
            ROUND(SUM(f.net_amount), 2) AS revenue,
            ROUND(SUM(f.profit), 2) AS profit
        FROM fact_sales f
        GROUP BY f.region, f.city, f.channel
        ORDER BY revenue DESC;

        CREATE VIEW vw_customer_summary AS
        SELECT
            customer_segment,
            COUNT(*) AS customer_count,
            ROUND(SUM(lifetime_spend), 2) AS segment_revenue,
            ROUND(AVG(lifetime_spend), 2) AS avg_customer_ltv
        FROM dim_customer
        GROUP BY customer_segment
        ORDER BY segment_revenue DESC;
        """
    )
    conn.commit()
    return conn


def verify_sql_kpis(clean_df: pd.DataFrame) -> dict:
    """Cross-verify SQL view KPIs against direct Pandas calculations."""
    conn = build_star_schema(clean_df)
    sql_kpis = pd.read_sql_query("SELECT * FROM vw_kpis", conn).iloc[0].to_dict()

    pd_rev = round(float(clean_df["net_amount"].sum()), 2)
    pd_prof = round(float(clean_df["profit"].sum()), 2)
    pd_orders = int(clean_df["transaction_id"].nunique())
    pd_aov = round(pd_rev / pd_orders, 2) if pd_orders else 0.0

    checks = {
        "sql_revenue": sql_kpis["total_revenue"],
        "pandas_revenue": pd_rev,
        "revenue_match": abs(sql_kpis["total_revenue"] - pd_rev) < 0.05,
        "sql_profit": sql_kpis["total_profit"],
        "pandas_profit": pd_prof,
        "profit_match": abs(sql_kpis["total_profit"] - pd_prof) < 0.05,
        "sql_orders": int(sql_kpis["total_orders"]),
        "pandas_orders": pd_orders,
        "orders_match": int(sql_kpis["total_orders"]) == pd_orders,
        "sql_aov": sql_kpis["avg_order_value"],
        "pandas_aov": pd_aov,
        "aov_match": abs(sql_kpis["avg_order_value"] - pd_aov) < 0.05,
    }
    return checks


if __name__ == "__main__":
    df = pd.read_csv("data/processed/smartmart_clean_sales.csv")
    conn = build_star_schema(df)

    print("=== Star Schema Tables Row Counts ===")
    for tbl in ["fact_sales", "dim_date", "dim_customer", "dim_product"]:
        cnt = pd.read_sql_query(f"SELECT COUNT(*) AS c FROM {tbl}", conn)["c"].iloc[0]
        print(f" - {tbl}: {cnt} rows")

    print("\n=== SQL KPI Verification ===")
    results = verify_sql_kpis(df)
    for k, v in results.items():
        print(f" - {k}: {v}")

    print("\n=== Category Performance (from SQL View) ===")
    print(pd.read_sql_query("SELECT * FROM vw_category_performance", conn).to_string(index=False))