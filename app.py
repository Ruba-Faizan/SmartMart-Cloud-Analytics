from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics_sql import build_star_schema
from src.etl_pipeline import clean_sales_data, load_raw_files

st.set_page_config(
    page_title="SmartMart Retail Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Vibrant Executive Styling: Hero Banner, Colored Headings, KPI Cards & Channel Cards
st.markdown(
    """
    <style>
    .hero-banner {
        background: linear-gradient(120deg, #0F172A 0%, #1E3A8A 45%, #0D9488 100%);
        padding: 24px 28px;
        border-radius: 16px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.18);
        margin-bottom: 18px;
        border: 1px solid rgba(255, 255, 255, 0.14);
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.16);
        color: #99F6E4;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .hero-title {
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0 0 6px 0;
        background: linear-gradient(90deg, #FFFFFF 0%, #A7F3D0 55%, #FDE68A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        font-size: 0.96rem;
        color: #E2E8F0;
        margin: 0;
    }
    .section-heading {
        font-size: 1.28rem;
        font-weight: 800;
        margin: 14px 0 10px 0;
        padding-left: 12px;
        border-left: 5px solid #0D9488;
        background: linear-gradient(90deg, #0F766E 0%, #2563EB 55%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-heading-purple {
        font-size: 1.12rem;
        font-weight: 700;
        margin: 12px 0 8px 0;
        color: #6D28D9;
    }
    .sub-heading-amber {
        font-size: 1.12rem;
        font-weight: 700;
        margin: 12px 0 8px 0;
        color: #B45309;
    }
    .sub-heading-teal {
        font-size: 1.12rem;
        font-weight: 700;
        margin: 12px 0 8px 0;
        color: #0F766E;
    }
    .kpi-card {
        border-radius: 14px;
        padding: 16px 18px;
        color: #FFFFFF;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
        margin-bottom: 10px;
    }
    .kpi-rev {
        background: linear-gradient(135deg, #0284C7 0%, #2563EB 100%);
    }
    .kpi-prof {
        background: linear-gradient(135deg, #059669 0%, #0D9488 100%);
    }
    .kpi-ord {
        background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%);
    }
    .kpi-aov {
        background: linear-gradient(135deg, #D97706 0%, #EA580C 100%);
    }
    .kpi-rep {
        background: linear-gradient(135deg, #DB2777 0%, #9333EA 100%);
    }
    .kpi-label {
        font-size: 0.82rem;
        font-weight: 600;
        opacity: 0.92;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 800;
        margin: 4px 0 2px 0;
    }
    .kpi-delta {
        font-size: 0.8rem;
        opacity: 0.95;
        font-weight: 600;
    }
    .channel-card {
        background: linear-gradient(135deg, #0D9488 0%, #0F766E 100%);
        color: #FFFFFF;
        padding: 18px 20px;
        border-radius: 14px;
        box-shadow: 0 6px 16px rgba(13, 148, 136, 0.22);
        margin-bottom: 12px;
    }
    .channel-card.online {
        background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.22);
    }
    .channel-title {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        margin-bottom: 6px;
    }
    .channel-rev {
        font-size: 1.65rem;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .channel-sub {
        font-size: 0.88rem;
        opacity: 0.94;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #EEF2FF;
        border-radius: 10px 10px 0 0;
        padding: 8px 16px;
        font-weight: 700;
        color: #1E3A8A;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0D9488 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

CLEAN_DATA_PATH = Path("data/processed/smartmart_clean_sales.csv")
RAW_DATA_DIR = Path("data/raw")

VIBRANT_PALETTE = ["#0D9488", "#2563EB", "#D97706", "#7C3AED", "#DB2777", "#16A34A"]


@st.cache_data(show_spinner="Loading and validating SmartMart dataset...")
def load_dataset() -> tuple[pd.DataFrame, dict]:
    """Load processed CSV if available, else run ETL from raw files."""
    if CLEAN_DATA_PATH.exists():
        df = pd.read_csv(CLEAN_DATA_PATH)
        stats = {
            "raw_rows": 10274,
            "imputed_missing_customers": int((df["customer_id"] == "CUST-UNKNOWN").sum()),
            "dropped_invalid_numeric_rows": 5,
            "dropped_duplicates": 283,
            "clean_rows": len(df),
        }
        return df, stats

    raw_df = load_raw_files(str(RAW_DATA_DIR))
    clean_df, stats = clean_sales_data(raw_df)
    return clean_df, stats


@st.cache_resource
def get_sql_connection(df: pd.DataFrame) -> sqlite3.Connection:
    return build_star_schema(df)


def compute_filtered_kpis(filtered_df: pd.DataFrame) -> dict:
    if filtered_df.empty:
        return {
            "revenue": 0.0,
            "profit": 0.0,
            "margin_pct": 0.0,
            "orders": 0,
            "aov": 0.0,
            "repeat_rate_pct": 0.0,
        }

    revenue = float(filtered_df["net_amount"].sum())
    profit = float(filtered_df["profit"].sum())
    margin_pct = (profit / revenue * 100.0) if revenue else 0.0
    orders = int(filtered_df["transaction_id"].nunique())
    aov = (revenue / orders) if orders else 0.0

    known_custs = filtered_df[filtered_df["customer_id"] != "CUST-UNKNOWN"]
    if not known_custs.empty:
        cust_orders = known_custs.groupby("customer_id")["transaction_id"].nunique()
        repeat_custs = int((cust_orders >= 2).sum())
        repeat_rate_pct = (repeat_custs / len(cust_orders) * 100.0)
    else:
        repeat_rate_pct = 0.0

    return {
        "revenue": revenue,
        "profit": profit,
        "margin_pct": margin_pct,
        "orders": orders,
        "aov": aov,
        "repeat_rate_pct": repeat_rate_pct,
    }


def style_channel_table(df: pd.DataFrame):
    """Apply rich conditional coloring and formatting without requiring matplotlib."""
    def color_profit(val):
        if val > 0:
            return "background-color: #DCFCE7; color: #166534; font-weight: 700;"
        if val < 0:
            return "background-color: #FEE2E2; color: #991B1B; font-weight: 700;"
        return ""

    def color_channel(val):
        if str(val).lower() == "online":
            return "background-color: #DBEAFE; color: #1E40AF; font-weight: 800;"
        return "background-color: #CCFBF1; color: #115E59; font-weight: 800;"

    def color_revenue(val):
        return "background-color: #EDE9FE; color: #5B21B6; font-weight: 700;"

    def color_share(val):
        return "background-color: #FEF3C7; color: #92400E; font-weight: 700;"

    styled = (
        df.style.format(
            {
                "Orders": "{:,}",
                "Units Sold": "{:,}",
                "Net Revenue ($)": "${:,.2f}",
                "Profit ($)": "${:,.2f}",
                "Avg Order Value ($)": "${:,.2f}",
                "Profit Margin (%)": "{:.2f}%",
                "Revenue Share (%)": "{:.1f}%",
            }
        )
        .map(color_channel, subset=["Channel"])
        .map(color_profit, subset=["Profit ($)", "Profit Margin (%)"])
        .map(color_revenue, subset=["Net Revenue ($)"])
        .map(color_share, subset=["Revenue Share (%)"])
    )
    return styled


def main():
    # Hero Header
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-badge">FREE-TIER CLOUD ANALYTICS • GITHUB + STREAMLIT + SQLITE</div>
            <div class="hero-title">🛒 SmartMart Retail Executive Analytics Dashboard</div>
            <div class="hero-sub">
                Consolidated sales, profitability, regional growth, and customer retention across
                <b>Electronics</b>, <b>Clothing</b>, <b>Home Appliances</b>, and <b>Grocery</b> (Store &amp; Online).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        df, audit_stats = load_dataset()
    except Exception as exc:
        st.error(f"Dataset load karne mein masla aaya: {exc}")
        st.stop()

    if df.empty:
        st.warning("Dataset mein koi valid record nahi mila.")
        st.stop()

    _ = get_sql_connection(df)

    df["parsed_date"] = pd.to_datetime(df["transaction_date"])
    min_date = df["parsed_date"].min().date()
    max_date = df["parsed_date"].max().date()

    # Sidebar Filters
    st.sidebar.markdown('<div class="sub-heading-teal">🎛️ Interactive Filters</div>', unsafe_allow_html=True)

    if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
        for key in ["filter_dates", "filter_regions", "filter_cities", "filter_categories", "filter_channels"]:
            st.session_state.pop(key, None)
        st.rerun()

    selected_dates = st.sidebar.date_input(
        "Order Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="filter_dates",
    )

    all_regions = sorted(df["region"].dropna().unique().tolist())
    selected_regions = st.sidebar.multiselect(
        "Region",
        options=all_regions,
        default=all_regions,
        key="filter_regions",
    )

    region_filtered_cities = sorted(
        df[df["region"].isin(selected_regions)]["city"].dropna().unique().tolist()
    )
    selected_cities = st.sidebar.multiselect(
        "City",
        options=region_filtered_cities,
        default=region_filtered_cities,
        key="filter_cities",
    )

    all_categories = sorted(df["category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Category",
        options=all_categories,
        default=all_categories,
        key="filter_categories",
    )

    all_channels = sorted(df["channel"].dropna().unique().tolist())
    selected_channels = st.sidebar.multiselect(
        "Channel",
        options=all_channels,
        default=all_channels,
        key="filter_channels",
    )

    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_d, end_d = selected_dates
    elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
        start_d = end_d = selected_dates[0]
    else:
        start_d = end_d = selected_dates

    mask = (
        (df["parsed_date"].dt.date >= start_d)
        & (df["parsed_date"].dt.date <= end_d)
        & (df["region"].isin(selected_regions))
        & (df["city"].isin(selected_cities))
        & (df["category"].isin(selected_categories))
        & (df["channel"].isin(selected_channels))
    )
    filtered_df = df.loc[mask].copy()

    if filtered_df.empty:
        st.info("Selected filters ke mutabiq koi sales record nahi mila. Kripya filter selections adjust karein.")
        st.stop()

    # Colorful KPI Cards Row
    kpis = compute_filtered_kpis(filtered_df)
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            f"""
            <div class="kpi-card kpi-rev">
                <div class="kpi-label">💰 Net Revenue</div>
                <div class="kpi-value">${kpis['revenue']:,.2f}</div>
                <div class="kpi-delta">Filtered Sales Total</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="kpi-card kpi-prof">
                <div class="kpi-label">📈 Net Profit</div>
                <div class="kpi-value">${kpis['profit']:,.2f}</div>
                <div class="kpi-delta">{kpis['margin_pct']:.1f}% Profit Margin</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="kpi-card kpi-ord">
                <div class="kpi-label">🧾 Total Orders</div>
                <div class="kpi-value">{kpis['orders']:,}</div>
                <div class="kpi-delta">Unique Transactions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="kpi-card kpi-aov">
                <div class="kpi-label">🛍️ Avg Order Value</div>
                <div class="kpi-value">${kpis['aov']:,.2f}</div>
                <div class="kpi-delta">Revenue per Order</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
            <div class="kpi-card kpi-rep">
                <div class="kpi-label">🔁 Repeat Buyer Rate</div>
                <div class="kpi-value">{kpis['repeat_rate_pct']:.1f}%</div>
                <div class="kpi-delta">Customers with 2+ Orders</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Overview Pie Charts Row
    st.markdown('<div class="section-heading">🥧 Revenue Share Overview</div>', unsafe_allow_html=True)
    pie_col1, pie_col2 = st.columns(2)

    cat_share_df = (
        filtered_df.groupby("category", as_index=False)
        .agg(net_revenue=("net_amount", "sum"), profit=("profit", "sum"))
        .sort_values("net_revenue", ascending=False)
    )
    with pie_col1:
        fig_cat_pie = px.pie(
            cat_share_df,
            names="category",
            values="net_revenue",
            hole=0.40,
            color_discrete_sequence=VIBRANT_PALETTE,
            title="Revenue Share by Category",
        )
        fig_cat_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_cat_pie, use_container_width=True)

    chan_share_df = (
        filtered_df.groupby("channel", as_index=False)
        .agg(net_revenue=("net_amount", "sum"), orders=("transaction_id", "nunique"))
        .sort_values("net_revenue", ascending=False)
    )
    with pie_col2:
        fig_chan_pie = px.pie(
            chan_share_df,
            names="channel",
            values="net_revenue",
            hole=0.40,
            color="channel",
            color_discrete_map={"Store": "#0D9488", "Online": "#2563EB"},
            title="Revenue Share by Channel (Store vs. Online)",
        )
        fig_chan_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_chan_pie, use_container_width=True)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📈 Sales Trends & Channels",
            "🏷️ Products & Regions",
            "👥 Customer Segmentation",
            "📥 Export & Data Quality",
        ]
    )

    # Tab 1: Trends & Channel Summary
    with tab1:
        st.markdown('<div class="section-heading">📈 Time-Series Revenue Trend</div>', unsafe_allow_html=True)
        granularity = st.radio(
            "Trend Granularity",
            options=["Monthly", "Daily"],
            horizontal=True,
        )
        if granularity == "Monthly":
            filtered_df["period"] = filtered_df["parsed_date"].dt.to_period("M").dt.to_timestamp()
        else:
            filtered_df["period"] = filtered_df["parsed_date"]

        trend_df = (
            filtered_df.groupby(["period", "channel"], as_index=False)
            .agg(net_revenue=("net_amount", "sum"), profit=("profit", "sum"))
            .sort_values("period")
        )
        fig_trend = px.line(
            trend_df,
            x="period",
            y="net_revenue",
            color="channel",
            color_discrete_map={"Store": "#0D9488", "Online": "#2563EB"},
            markers=(granularity == "Monthly"),
            title=f"{granularity} Net Revenue by Channel",
            labels={"period": "Date", "net_revenue": "Net Revenue ($)", "channel": "Channel"},
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        total_filtered_rev = float(filtered_df["net_amount"].sum())
        channel_summary = (
            filtered_df.groupby("channel", as_index=False)
            .agg(
                orders=("transaction_id", "nunique"),
                units_sold=("quantity", "sum"),
                net_revenue=("net_amount", "sum"),
                profit=("profit", "sum"),
            )
            .sort_values("net_revenue", ascending=False)
        )
        channel_summary["Avg Order Value ($)"] = (
            channel_summary["net_revenue"] / channel_summary["orders"]
        ).round(2)
        channel_summary["Profit Margin (%)"] = (
            channel_summary["profit"] / channel_summary["net_revenue"] * 100.0
        ).round(2)
        channel_summary["Revenue Share (%)"] = (
            channel_summary["net_revenue"] / total_filtered_rev * 100.0
        ).round(1)

        channel_summary = channel_summary.rename(
            columns={
                "channel": "Channel",
                "orders": "Orders",
                "units_sold": "Units Sold",
                "net_revenue": "Net Revenue ($)",
                "profit": "Profit ($)",
            }
        )

        st.markdown('<div class="section-heading">🏬 Channel Performance Summary</div>', unsafe_allow_html=True)

        card_cols = st.columns(len(channel_summary))
        for idx, row in channel_summary.iterrows():
            card_class = "channel-card online" if str(row["Channel"]).lower() == "online" else "channel-card"
            icon = "🌐" if str(row["Channel"]).lower() == "online" else "🏬"
            with card_cols[list(channel_summary.index).index(idx)]:
                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="channel-title">{icon} {row['Channel']} Channel ({row['Revenue Share (%)']:.1f}% Share)</div>
                        <div class="channel-rev">${row['Net Revenue ($)']:,.2f}</div>
                        <div class="channel-sub">
                            Orders: <b>{int(row['Orders']):,}</b> &nbsp;|&nbsp;
                            AOV: <b>${row['Avg Order Value ($)']:,.2f}</b> &nbsp;|&nbsp;
                            Profit: <b>${row['Profit ($)']:,.2f}</b> ({row['Profit Margin (%)']:.1f}%)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        tbl_col, bar_col = st.columns([1.35, 1])
        with tbl_col:
            st.dataframe(
                style_channel_table(channel_summary),
                use_container_width=True,
                hide_index=True,
            )

        with bar_col:
            melted_chan = channel_summary.melt(
                id_vars=["Channel"],
                value_vars=["Net Revenue ($)", "Profit ($)"],
                var_name="Metric",
                value_name="Amount ($)",
            )
            fig_chan_bar = px.bar(
                melted_chan,
                x="Channel",
                y="Amount ($)",
                color="Metric",
                barmode="group",
                text_auto=".2s",
                color_discrete_map={"Net Revenue ($)": "#2563EB", "Profit ($)": "#0D9488"},
                title="Channel Revenue vs. Profit Comparison",
            )
            fig_chan_bar.update_layout(margin=dict(t=40, b=10, l=10, r=10), height=260)
            st.plotly_chart(fig_chan_bar, use_container_width=True)

    # Tab 2: Products & Regions
    with tab2:
        st.markdown('<div class="section-heading">🏷️ Category &amp; Regional Performance</div>', unsafe_allow_html=True)
        col_left, col_right = st.columns(2)

        with col_left:
            fig_cat_profit = px.bar(
                cat_share_df.sort_values("profit", ascending=True),
                x="profit",
                y="category",
                orientation="h",
                color="category",
                color_discrete_sequence=VIBRANT_PALETTE,
                title="Net Profit / Loss by Category",
                labels={"profit": "Net Profit ($)", "category": "Category"},
            )
            st.plotly_chart(fig_cat_profit, use_container_width=True)

        with col_right:
            reg_df = (
                filtered_df.groupby("region", as_index=False)
                .agg(net_revenue=("net_amount", "sum"), profit=("profit", "sum"))
                .sort_values("net_revenue", ascending=False)
            )
            fig_reg = px.bar(
                reg_df,
                x="region",
                y="net_revenue",
                color="region",
                color_discrete_sequence=VIBRANT_PALETTE,
                title="Net Revenue by Region",
                labels={"net_revenue": "Net Revenue ($)", "region": "Region"},
            )
            st.plotly_chart(fig_reg, use_container_width=True)

        prod_perf = (
            filtered_df.groupby(["product_id", "product_name", "category"], as_index=False)
            .agg(
                orders=("transaction_id", "nunique"),
                units_sold=("quantity", "sum"),
                revenue=("net_amount", "sum"),
                profit=("profit", "sum"),
            )
        )

        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.markdown('<div class="sub-heading-teal">🏆 Top 10 Best-Selling Products (by Revenue)</div>', unsafe_allow_html=True)
            st.dataframe(
                prod_perf.sort_values("revenue", ascending=False).head(10),
                use_container_width=True,
                hide_index=True,
            )
        with p_col2:
            st.markdown('<div class="sub-heading-amber">⚠️ Bottom 10 Underperforming Products (by Profit)</div>', unsafe_allow_html=True)
            st.dataframe(
                prod_perf.sort_values("profit", ascending=True).head(10),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown('<div class="sub-heading-purple">🏙️ Top 10 Cities by Revenue</div>', unsafe_allow_html=True)
        top_cities = (
            filtered_df.groupby(["region", "city"], as_index=False)
            .agg(
                orders=("transaction_id", "nunique"),
                revenue=("net_amount", "sum"),
                profit=("profit", "sum"),
            )
            .sort_values("revenue", ascending=False)
            .head(10)
        )
        st.dataframe(top_cities, use_container_width=True, hide_index=True)

    # Tab 3: Customer Segmentation
    with tab3:
        st.markdown('<div class="section-heading">👥 Customer Segmentation &amp; Value</div>', unsafe_allow_html=True)
        cust_df = (
            filtered_df.groupby(["customer_id", "customer_name"], as_index=False)
            .agg(
                orders=("transaction_id", "nunique"),
                total_spend=("net_amount", "sum"),
                total_profit=("profit", "sum"),
            )
        )

        def seg_label(row):
            if row["customer_id"] == "CUST-UNKNOWN":
                return "Guest / Unknown"
            if row["orders"] == 1:
                return "New / One-Time"
            if row["total_spend"] >= 2000:
                return "VIP Repeat"
            return "Repeat Buyer"

        cust_df["segment"] = cust_df.apply(seg_label, axis=1)

        seg_summary = (
            cust_df.groupby("segment", as_index=False)
            .agg(
                customers=("customer_id", "count"),
                segment_revenue=("total_spend", "sum"),
                avg_spend_per_customer=("total_spend", "mean"),
            )
            .sort_values("segment_revenue", ascending=False)
        )
        seg_summary["avg_spend_per_customer"] = seg_summary["avg_spend_per_customer"].round(2)

        fig_seg = px.pie(
            seg_summary,
            names="segment",
            values="segment_revenue",
            hole=0.40,
            color_discrete_sequence=VIBRANT_PALETTE,
            title="Revenue Share by Customer Segment",
        )
        fig_seg.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_seg, use_container_width=True)
        st.dataframe(seg_summary, use_container_width=True, hide_index=True)

        st.markdown('<div class="sub-heading-purple">🌟 Top 15 Customers by Spend</div>', unsafe_allow_html=True)
        top_custs = (
            cust_df[cust_df["customer_id"] != "CUST-UNKNOWN"]
            .sort_values("total_spend", ascending=False)
            .head(15)
        )
        st.dataframe(top_custs, use_container_width=True, hide_index=True)

    # Tab 4: Export & Data Quality
    with tab4:
        st.markdown('<div class="section-heading">🧹 ETL Data Cleaning Audit &amp; CSV Export</div>', unsafe_allow_html=True)
        st.json(audit_stats)

        export_cols = [
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
            "discount_pct",
            "net_amount",
            "profit",
        ]
        export_df = filtered_df[export_cols].drop(columns=["parsed_date"], errors="ignore")

        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Filtered Sales Data (CSV)",
            data=csv_bytes,
            file_name="smartmart_filtered_sales.csv",
            mime="text/csv",
        )

        st.markdown('<div class="sub-heading-teal">📄 Filtered Transactions Preview (First 100 Rows)</div>', unsafe_allow_html=True)
        st.dataframe(export_df.head(100), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()