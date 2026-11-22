# SmartMart Retail — Free-Tier Cloud Analytics Solution

An end-to-end retail analytics platform built for **SmartMart Retail** using **Python**, **SQLite (In-Memory Star Schema)**, **Streamlit**, and **GitHub + Streamlit Community Cloud**—requiring **$0 paid cloud infrastructure**.

## 1. Business Scenario & Problem Addressed
SmartMart Retail sells **Electronics**, **Clothing**, **Home Appliances**, and **Grocery** items across physical stores (`Store`) and e-commerce (`Online`). Previously, sales exports lived in fragmented Excel and CSV files with duplicate records, inconsistent text casing, and missing customer IDs.

This solution automates:
1. **Multi-file ETL & Data Cleaning (`src/etl_pipeline.py`)**: Merges Excel/CSV exports, trims/standardizes categories and regions, imputes missing customer IDs (`CUST-UNKNOWN`), drops invalid quantities (`<= 0`), removes duplicate `(transaction_id, product_id)` rows, and computes `gross_amount`, `net_amount`, and `profit`.
2. **Dimensional Star Schema & SQL Views (`src/analytics_sql.py`)**: Builds `fact_sales`, `dim_date`, `dim_customer`, and `dim_product` in an in-memory SQLite engine with views (`vw_kpis`, `vw_category_performance`, `vw_regional_performance`, `vw_customer_summary`) verified against Pandas.
3. **Interactive Executive Dashboard (`app.py`)**: Provides KPI cards, category/channel pie charts, time-series trends, product/region rankings, customer segmentation (`VIP Repeat`, `Repeat Buyer`, `New / One-Time`, `Guest / Unknown`), and filtered CSV exports.

## 2. Project Structure
```text
Cloud_project/
├── .streamlit/
│   └── config.toml                  # Custom UI theme
├── data/
│   ├── raw/                         # Raw multi-format Excel/CSV exports
│   └── processed/
│       └── smartmart_clean_sales.csv
├── src/
│   ├── prepare_raw_data.py          # Raw dataset preparation script
│   ├── etl_pipeline.py              # Cleaning, validation & deduplication
│   ├── analytics_sql.py             # Star schema & SQL KPI verification
│   └── test_suite.py                # Automated validation & edge-case tests
├── app.py                           # Main Streamlit web application
├── requirements.txt                 # Cloud deployment dependencies
└── README.md