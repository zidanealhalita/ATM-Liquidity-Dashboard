"""
ATM Network Liquidity Optimization Dashboard
==============================================
Operations & Treasury - Cash Liquidity Optimization for ATM Network

Dashboard interaktif untuk menganalisis kinerja kas jaringan ATM, mengukur
peluang efisiensi biaya berbasis model Economic Order Quantity (EOQ), dan
menghasilkan rekomendasi kebijakan isi ulang (replenishment) yang berbasis data.

Jalankan dengan:
    streamlit run app.py
"""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="ATM Liquidity Optimization",
    page_icon="\U0001F3E6",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# THEME / COLORS  (selaras dengan deck & workbook: "Midnight Executive")
# =====================================================================
NAVY = "#1E2761"
NAVY_DEEP = "#141B49"
ICE = "#CADCFC"
ICE_SOFT = "#EEF2FC"
GOLD = "#C9971C"
GOLD_SOFT = "#F3E6C4"
SLATE = "#3D4152"
MUTE = "#6E7488"
CORAL = "#B3452C"
GREEN = "#1E7145"

CATEGORY_COLORS = [NAVY, GOLD, "#5B6BAE", "#D9B24C", "#8B95C9"]
SEQ_COLORS = [ICE, "#8FA6E0", NAVY]

PLOTLY_TEMPLATE = "plotly_grey"

def style_fig(fig, height=420, legend_bottom=True, title=None):
    """Apply consistent styling to a plotly figure."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        font=dict(family="Calibri, Arial", size=13, color=SLATE),
        title=dict(text=title, font=dict(size=16, color=NAVY, family="Cambria, Georgia, serif")) if title else None,
        margin=dict(l=10, r=10, t=50 if title else 20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5) if legend_bottom else {},
        plot_bgcolor="white",
        paper_bgcolor="white",
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Calibri"),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="#DCE1EE")
    fig.update_yaxes(showgrid=True, gridcolor="#EEF1F8", zeroline=False)
    return fig


# =====================================================================
# CUSTOM CSS
# =====================================================================
st.markdown(f"""
<style>
    .stApp {{ background-color: #FAFBFE; }}
    #MainMenu, footer {{ visibility: hidden; }}

    .app-header {{
        background: linear-gradient(120deg, {NAVY_DEEP} 0%, {NAVY} 100%);
        padding: 1.8rem 2.2rem; border-radius: 14px; margin-bottom: 1.4rem;
        color: white;
    }}
    .app-header .kicker {{
        color: {GOLD}; font-size: 0.82rem; font-weight: 700; letter-spacing: 2px;
        text-transform: uppercase; margin-bottom: 0.3rem;
    }}
    .app-header h1 {{ color: white; font-size: 2rem; margin: 0 0 0.35rem 0; font-weight: 700; }}
    .app-header p {{ color: {ICE}; font-size: 0.95rem; margin: 0; }}

    div[data-testid="stMetric"] {{
        background: #0B0C10; /* Hitam pekat premium */
        border: 1px solid #1F2833; 
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        min-height: 120px;
    }}
    
    div[data-testid="stMetricLabel"] {{ 
        color: {ICE} !important; 
        font-size: 0.85rem; 
        font-weight: 500;
        letter-spacing: 0.5px;
    }}
    
    div[data-testid="stMetricValue"] {{ 
        color: #FFFFFF !important; 
        font-weight: 700; 
        font-size: 1.85rem !important; 
        white-space: nowrap !important;
    }}

    div[data-testid="stMetricDelta"] div {{
        white-space: normal !important;
        word-break: break-word !important;
    }}

    .insight-box {{
        background: {ICE_SOFT}; border-left: 4px solid {NAVY};
        border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.6rem 0;
        font-size: 0.92rem; color: {SLATE};
    }}
    .insight-box b {{ color: {NAVY}; }}
    .gold-box {{
        background: {GOLD_SOFT}; border-left: 4px solid {GOLD};
        border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.6rem 0;
        font-size: 0.92rem; color: {SLATE};
    }}
    .gold-box b {{ color: #8A6A10; }}
    .risk-box {{
        background: #FBEAE5; border-left: 4px solid {CORAL};
        border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.6rem 0;
        font-size: 0.92rem; color: {SLATE};
    }}
    .risk-box b {{ color: {CORAL}; }}

    .section-title {{
        color: {NAVY}; font-size: 1.25rem; font-weight: 700; margin: 0.2rem 0 0.6rem 0;
        border-bottom: 2px solid {ICE}; padding-bottom: 0.4rem;
    }}
    .rec-card {{
        background: white; border: 1px solid #E3E7F2; border-radius: 12px;
        padding: 1rem 1.2rem; margin-bottom: 0.7rem;
    }}
    .rec-num {{
        display:inline-block; background:{NAVY}; color:white; width:28px; height:28px;
        border-radius:50%; text-align:center; line-height:28px; font-weight:700; margin-right:10px;
    }}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


# =====================================================================
# DATA LOADING
# =====================================================================
REQUIRED_COLS = [
    "Log_Date", "ATM_ID", "Location_Type", "Region", "Max_Capacity_IDR",
    "Beginning_Cash_IDR", "Replenishment_Amount_IDR", "Target_Demand_IDR",
    "Actual_Withdrawal_IDR", "Ending_Cash_IDR", "Is_Stockout",
    "Holding_Cost_IDR", "Logistics_Cost_IDR", "Stockout_Penalty_Cost_IDR",
]


@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan pada dataset: {', '.join(missing)}")
    df["Log_Date"] = pd.to_datetime(df["Log_Date"])
    df = df.sort_values(["ATM_ID", "Log_Date"]).reset_index(drop=True)
    df["Day_Name"] = df["Log_Date"].dt.day_name()
    df["Is_Weekend"] = df["Log_Date"].dt.dayofweek >= 5
    df["Month"] = df["Log_Date"].dt.to_period("M").astype(str)
    df["Utilization_Pct"] = df["Beginning_Cash_IDR"] / df["Max_Capacity_IDR"] * 100
    df["Is_Replenishment"] = df["Replenishment_Amount_IDR"] > 0
    df.loc[df["Is_Replenishment"], "PreRefill_Pct"] = (
        df.loc[df["Is_Replenishment"], "Beginning_Cash_IDR"]
        / df.loc[df["Is_Replenishment"], "Max_Capacity_IDR"] * 100
    )
    return df


@st.cache_data(show_spinner=False)
def compute_atm_summary(df: pd.DataFrame, holding_rate_annual_pct: float, capacity_cap: float = 0.999) -> pd.DataFrame:
    """
    Hitung ringkasan per-ATM termasuk kuantitas order optimal (EOQ) dan
    estimasi potensi penghematan tahunan, berdasarkan trade-off antara
    biaya modal dana idle (holding cost) dan biaya logistik CIT per trip.

        Q* = sqrt( 2 * D * S / H )

    D = rata-rata penarikan harian, S = biaya logistik per trip,
    H = tingkat biaya modal harian (opportunity cost dana idle).
    """
    h_daily = (holding_rate_annual_pct / 100) / 365

    g = df.groupby("ATM_ID").agg(
        Location_Type=("Location_Type", "first"),
        Region=("Region", "first"),
        Max_Capacity=("Max_Capacity_IDR", "first"),
        Days=("Log_Date", "count"),
        Avg_Beginning=("Beginning_Cash_IDR", "mean"),
        Avg_Withdrawal=("Actual_Withdrawal_IDR", "mean"),
        Std_Withdrawal=("Actual_Withdrawal_IDR", "std"),
        Total_Withdrawal=("Actual_Withdrawal_IDR", "sum"),
        Total_Replenishment=("Replenishment_Amount_IDR", "sum"),
        Total_Holding=("Holding_Cost_IDR", "sum"),
        Total_Logistics=("Logistics_Cost_IDR", "sum"),
        Total_Stockout_Days=("Is_Stockout", "sum"),
        Trips=("Is_Replenishment", "sum"),
    ).reset_index()

    g["Std_Withdrawal"] = g["Std_Withdrawal"].fillna(0)
    g["Util_Pct"] = g["Avg_Beginning"] / g["Max_Capacity"] * 100
    g["CV_Demand"] = (g["Std_Withdrawal"] / g["Avg_Withdrawal"]).replace([np.inf, -np.inf], np.nan)
    g["Avg_Cycle_Days"] = g["Days"] / g["Trips"].replace(0, np.nan)
    g["Avg_Logistics_per_Trip"] = g["Total_Logistics"] / g["Trips"].replace(0, np.nan)
    g["Total_Cost"] = g["Total_Holding"] + g["Total_Logistics"]
    g["Actual_Daily_Cost"] = g["Total_Cost"] / g["Days"]

    valid = g["Avg_Logistics_per_Trip"].notna() & (g["Avg_Logistics_per_Trip"] > 0) & (h_daily > 0)
    g["EOQ_Qty"] = np.where(
        valid, np.sqrt(2 * g["Avg_Withdrawal"] * g["Avg_Logistics_per_Trip"].fillna(0) / max(h_daily, 1e-12)), np.nan
    )
    g["EOQ_Qty_Constrained"] = np.minimum(g["EOQ_Qty"], g["Max_Capacity"] * capacity_cap)
    g["EOQ_Daily_Cost"] = (
        (g["Avg_Withdrawal"] / g["EOQ_Qty_Constrained"]) * g["Avg_Logistics_per_Trip"]
        + (g["EOQ_Qty_Constrained"] / 2) * h_daily
    )
    g["EOQ_Cycle_Days"] = g["EOQ_Qty_Constrained"] / g["Avg_Withdrawal"]
    g["Annual_Savings"] = ((g["Actual_Daily_Cost"] - g["EOQ_Daily_Cost"]) * 365).clip(lower=0)
    g["Annual_Cost_Current"] = g["Actual_Daily_Cost"] * 365
    g["Savings_Pct"] = np.where(g["Annual_Cost_Current"] > 0, g["Annual_Savings"] / g["Annual_Cost_Current"] * 100, 0)
    g["EOQ_Feasible"] = g["EOQ_Qty"] < g["Max_Capacity"]
    g["Annual_Savings"] = g["Annual_Savings"].fillna(0)
    return g


@st.cache_data(show_spinner=False)
def compute_location_summary(df: pd.DataFrame, atm_summary: pd.DataFrame) -> pd.DataFrame:
    loc = df.groupby("Location_Type").agg(
        ATMs=("ATM_ID", "nunique"),
        Avg_Capacity=("Max_Capacity_IDR", "mean"),
        Avg_Withdrawal=("Actual_Withdrawal_IDR", "mean"),
        Total_Holding=("Holding_Cost_IDR", "sum"),
        Total_Logistics=("Logistics_Cost_IDR", "sum"),
        Days=("Log_Date", "count"),
    ).reset_index()
    cv = df.groupby("Location_Type")["Actual_Withdrawal_IDR"].agg(["mean", "std"]).reset_index()
    cv["CV"] = cv["std"] / cv["mean"]
    loc = loc.merge(cv[["Location_Type", "CV"]], on="Location_Type", how="left")

    util = atm_summary.groupby("Location_Type")["Util_Pct"].mean().reset_index().rename(columns={"Util_Pct": "Avg_Util_Pct"})
    loc = loc.merge(util, on="Location_Type", how="left")

    savings = atm_summary.groupby("Location_Type")["Annual_Savings"].sum().reset_index()
    loc = loc.merge(savings, on="Location_Type", how="left")

    wk = df.groupby(["Location_Type", "Is_Weekend"])["Actual_Withdrawal_IDR"].mean().unstack()
    wk = wk.rename(columns={False: "Weekday_Avg", True: "Weekend_Avg"}).reset_index()
    loc = loc.merge(wk, on="Location_Type", how="left")
    loc["Weekend_Uplift_Pct"] = (loc["Weekend_Avg"] - loc["Weekday_Avg"]) / loc["Weekday_Avg"] * 100

    trip_cost = df[df["Is_Replenishment"]].groupby("Location_Type")["Logistics_Cost_IDR"].mean().reset_index()
    trip_cost.columns = ["Location_Type", "Avg_Logistics_per_Trip"]
    loc = loc.merge(trip_cost, on="Location_Type", how="left")

    # Annualize using days-PER-ATM (not total row count) so groups with more
    # ATMs aren't under-annualized.
    days_per_atm = (
        df.groupby(["Location_Type", "ATM_ID"])["Log_Date"].count()
        .reset_index().groupby("Location_Type")["Log_Date"].mean()
    )
    loc = loc.merge(days_per_atm.rename("Days_Per_ATM"), on="Location_Type", how="left")
    loc["Holding_Annual"] = loc["Total_Holding"] / loc["Days_Per_ATM"] * 365
    loc["Logistics_Annual"] = loc["Total_Logistics"] / loc["Days_Per_ATM"] * 365
    loc["Annual_Cost"] = loc["Holding_Annual"] + loc["Logistics_Annual"]
    return loc


@st.cache_data(show_spinner=False)
def compute_region_summary(df: pd.DataFrame) -> pd.DataFrame:
    reg = df.groupby("Region").agg(
        ATMs=("ATM_ID", "nunique"),
        Total_Withdrawal=("Actual_Withdrawal_IDR", "sum"),
        Total_Holding=("Holding_Cost_IDR", "sum"),
        Total_Logistics=("Logistics_Cost_IDR", "sum"),
        Trips=("Is_Replenishment", "sum"),
    ).reset_index()
    days_per_atm = (
        df.groupby(["Region", "ATM_ID"])["Log_Date"].count()
        .reset_index().groupby("Region")["Log_Date"].mean()
    )
    reg = reg.merge(days_per_atm.rename("Days_Per_ATM"), on="Region", how="left")
    reg["Annual_Cost"] = (reg["Total_Holding"] + reg["Total_Logistics"]) / reg["Days_Per_ATM"] * 365
    reg["Cost_per_ATM"] = reg["Annual_Cost"] / reg["ATMs"]
    reg["Avg_Logistics_per_Trip"] = reg["Total_Logistics"] / reg["Trips"].replace(0, np.nan)
    return reg


# =====================================================================
# FORMAT HELPERS
# =====================================================================
def fmt_rp(n, decimals=0):
    if pd.isna(n):
        return "-"
    return "Rp" + f"{n:,.{decimals}f}".replace(",", "@").replace(".", ",").replace("@", ".")

def fmt_rp_jt(n):
    if pd.isna(n):
        return "-"
    return fmt_rp(n / 1e6, 1) + " Jt"

def fmt_rp_m(n):
    if pd.isna(n):
        return "-"
    return fmt_rp(n / 1e9, 2) + " M"

def fmt_pct(n, decimals=1):
    if pd.isna(n):
        return "-"
    return f"{n:,.{decimals}f}".replace(".", ",") + "%"

def fmt_num(n, decimals=0):
    if pd.isna(n):
        return "-"
    return f"{n:,.{decimals}f}".replace(",", "@").replace(".", ",").replace("@", ".")



# =====================================================================
# SIDEBAR — SUMBER DATA, FILTER, ASUMSI
# =====================================================================
with st.sidebar:
    st.markdown(
        f"<div style='padding:0.3rem 0 0.2rem 0;font-size:1.7rem;'>\U0001F3E6</div>"
        f"<div style='color:{NAVY}; font-size:1.15rem; font-weight:700; line-height:1.25;'>ATM Liquidity<br>Optimizer</div>",
        unsafe_allow_html=True,
    )
    st.caption("Operations & Treasury \u2014 Cash Liquidity Optimization")
    st.divider()

    st.markdown("**\U0001F4C2 Sumber Data**")
    uploaded = st.file_uploader(
        "Unggah dataset CSV (opsional)", type=["csv"],
        help="Kosongkan untuk memakai dataset contoh bawaan (20 ATM x 200 hari). "
             "Dataset kustom harus memiliki kolom yang sama dengan format contoh.",
    )
    default_csv_path = Path(__file__).parent / "atm_liquidity_optimization_dataset.csv"

    try:
        if uploaded is not None:
            raw_bytes = uploaded.getvalue()
            data_source_label = f"File diunggah: {uploaded.name}"
        else:
            raw_bytes = default_csv_path.read_bytes()
            data_source_label = "Dataset contoh bawaan (20 ATM \u00D7 200 hari)"
        df_all = load_data(raw_bytes)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    st.caption(f"\u2713 {data_source_label}")
    st.divider()

    st.markdown("**\U0001F50D Filter Data**")

    loc_options = sorted(df_all["Location_Type"].unique().tolist())
    sel_loc = st.multiselect("Tipe Lokasi", loc_options, default=loc_options)

    region_options = sorted(df_all["Region"].unique().tolist())
    sel_region = st.multiselect("Wilayah", region_options, default=region_options)

    atm_options = sorted(df_all["ATM_ID"].unique().tolist())
    sel_atm = st.multiselect("ATM (opsional, kosongkan = semua)", atm_options, default=[])

    min_d, max_d = df_all["Log_Date"].min().date(), df_all["Log_Date"].max().date()
    sel_dates = st.date_input(
        "Rentang Tanggal", value=(min_d, max_d), min_value=min_d, max_value=max_d,
    )

    if st.button("\u21BB Reset Filter", width="stretch"):
        st.rerun()

    st.divider()
    st.markdown("**\u2699\uFE0F Asumsi Model EOQ**")

    _implied_rate = (df_all["Holding_Cost_IDR"] / df_all["Beginning_Cash_IDR"]).replace([np.inf, -np.inf], np.nan)
    _implied_annual_pct = float(_implied_rate.median() * 365 * 100)

    holding_rate = st.slider(
        "Tingkat biaya modal tahunan (%)", min_value=1.0, max_value=15.0,
        value=round(_implied_annual_pct, 1), step=0.1,
        help="Opportunity cost dana idle di ATM per tahun. Nilai default diturunkan otomatis dari "
             "median rasio Holding_Cost \u00F7 Saldo Kas pada dataset (\u2248 mendekati BI 7-Day Reverse Repo Rate).",
    )
    st.caption(f"\U0001F4A1 Tingkat implisit dari data: \u2248{_implied_annual_pct:.2f}%/tahun")

    with st.expander("Pengaturan lanjutan"):
        capacity_cap = st.slider(
            "Batas kapasitas EOQ (% dari kapasitas fisik)", min_value=80, max_value=100, value=100, step=1,
            help="Kuantitas order EOQ tidak boleh melebihi persentase ini dari kapasitas maksimum ATM.",
        ) / 100.0
        if capacity_cap >= 1.0:
            capacity_cap = 0.999

    st.divider()
    st.caption("Dibangun untuk Divisi Operations & Treasury \u2014 Juli 2026")

# =====================================================================
# APPLY FILTERS
# =====================================================================
if isinstance(sel_dates, (tuple, list)) and len(sel_dates) == 2:
    date_start, date_end = sel_dates[0], sel_dates[1]
elif isinstance(sel_dates, (tuple, list)) and len(sel_dates) == 1:
    date_start, date_end = sel_dates[0], sel_dates[0]
else:
    date_start, date_end = sel_dates, sel_dates

mask = (
    df_all["Location_Type"].isin(sel_loc)
    & df_all["Region"].isin(sel_region)
    & (df_all["Log_Date"].dt.date >= date_start)
    & (df_all["Log_Date"].dt.date <= date_end)
)
if sel_atm:
    mask &= df_all["ATM_ID"].isin(sel_atm)

df = df_all[mask].copy()

if df.empty or df["ATM_ID"].nunique() == 0:
    st.warning("Tidak ada data yang cocok dengan filter saat ini. Silakan sesuaikan filter di sidebar.")
    st.stop()

n_days_selected = df.groupby("ATM_ID")["Log_Date"].count().max()

atm_summary = compute_atm_summary(df, holding_rate, capacity_cap)
loc_summary = compute_location_summary(df, atm_summary)
region_summary = compute_region_summary(df)


# =====================================================================
# HEADER
# =====================================================================
period_str = f"{df['Log_Date'].min().strftime('%d %b %Y')} \u2013 {df['Log_Date'].max().strftime('%d %b %Y')}"
st.markdown(f"""
<div class="app-header">
    <div class="kicker">OPERATIONS & TREASURY</div>
    <h1>\U0001F3E6 ATM Network Liquidity Optimization Dashboard</h1>
    <p>Analisis kas &amp; kebijakan isi ulang ATM berbasis data \u2014 {df['ATM_ID'].nunique()} unit ATM
    &bull; {period_str} &bull; {n_days_selected} hari observasi/ATM</p>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# KPI ROW
# =====================================================================
total_withdrawal = df["Actual_Withdrawal_IDR"].sum()
total_holding_annual = df["Holding_Cost_IDR"].sum() / n_days_selected * 365
total_logistics_annual = df["Logistics_Cost_IDR"].sum() / n_days_selected * 365
total_cost_annual = total_holding_annual + total_logistics_annual
total_savings = atm_summary["Annual_Savings"].sum()
savings_pct = (total_savings / total_cost_annual * 100) if total_cost_annual > 0 else 0
avg_util = atm_summary["Util_Pct"].mean()
stockout_days = int(df["Is_Stockout"].sum())
trips_total = int(atm_summary["Trips"].sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total ATM", f"{df['ATM_ID'].nunique()} unit")
k2.metric("Volume Penarikan", fmt_rp_m(total_withdrawal))
k3.metric("Utilisasi Kas Rata2", fmt_pct(avg_util))
k4.metric("Biaya Operasional /Thn", fmt_rp_jt(total_cost_annual))
k5.metric("Potensi Hemat EOQ /Thn", fmt_rp_jt(total_savings), delta=f"{savings_pct:.1f}% dari biaya saat ini")
k6.metric("Insiden Stockout", f"{stockout_days}", delta=f"dari {trips_total} trip isi ulang" if trips_total else None, delta_color="off")

st.write("")

# =====================================================================
# TABS
# =====================================================================
tab_labels = [
    "\U0001F4CA Ringkasan Eksekutif",
    "\U0001F4B0 Biaya & Utilisasi",
    "\U0001F3AF Optimasi EOQ",
    "\U0001F4C8 Volatilitas & Musiman",
    "\U0001F5FA\uFE0F Wilayah & Logistik",
    "\U0001F501 Kebijakan Replenishment",
    "\U0001F4CB Rekomendasi",
    "\U0001F4C1 Data Explorer",
]
tabs = st.tabs(tab_labels)


# =====================================================================
# TAB 1 — RINGKASAN EKSEKUTIF
# =====================================================================
with tabs[0]:
    c1, c2 = st.columns([1.3, 1])

    with c1:
        st.markdown('<div class="section-title">Struktur Biaya per Tipe Lokasi</div>', unsafe_allow_html=True)
        loc_sorted = loc_summary.sort_values("Annual_Cost", ascending=True)
        fig = go.Figure()
        fig.add_bar(y=loc_sorted["Location_Type"], x=loc_sorted["Holding_Annual"], name="Biaya Modal (Holding)",
                    orientation="h", marker_color=NAVY,
                    hovertemplate="%{y}<br>Holding: Rp%{x:,.0f}<extra></extra>")
        fig.add_bar(y=loc_sorted["Location_Type"], x=loc_sorted["Logistics_Annual"], name="Biaya Logistik (CIT)",
                    orientation="h", marker_color=GOLD,
                    hovertemplate="%{y}<br>Logistik: Rp%{x:,.0f}<extra></extra>")
        fig.update_layout(barmode="stack")
        fig = style_fig(fig, height=360)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown('<div class="section-title">Tren Bulanan Penarikan</div>', unsafe_allow_html=True)
        monthly = df.groupby("Month")["Actual_Withdrawal_IDR"].sum().reset_index()
        fig2 = px.line(monthly, x="Month", y="Actual_Withdrawal_IDR", markers=True,
                        color_discrete_sequence=[NAVY])
        fig2.update_traces(line_width=3, hovertemplate="%{x}<br>Rp%{y:,.0f}<extra></extra>")
        fig2 = style_fig(fig2, height=360)
        fig2.update_yaxes(title=None)
        fig2.update_xaxes(title=None)
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-title">Temuan Utama (Otomatis dari Data Terfilter)</div>', unsafe_allow_html=True)

    top_cost_loc = loc_summary.loc[loc_summary["Annual_Cost"].idxmax()]
    top_savings_loc = loc_summary.loc[loc_summary["Annual_Savings"].idxmax()]
    top2_savings_share = loc_summary.nlargest(2, "Annual_Savings")["Annual_Savings"].sum() / max(total_savings, 1e-9) * 100
    idle_pct = 100 - avg_util

    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.markdown(f"""<div class="insight-box">
        <b>Rp{total_savings/1e6:,.1f} Jt/tahun ({savings_pct:.1f}%)</b><br>
        potensi penghematan biaya operasional dari right-sizing kuantitas isi ulang (EOQ),
        tanpa menambah risiko stockout.</div>""", unsafe_allow_html=True)
    with ic2:
        st.markdown(f"""<div class="gold-box">
        <b>{top2_savings_share:.0f}%</b> dari total potensi penghematan terkonsentrasi pada
        2 tipe lokasi terbesar: <b>{', '.join(loc_summary.nlargest(2,'Annual_Savings')['Location_Type'])}</b>.</div>""", unsafe_allow_html=True)
    with ic3:
        st.markdown(f"""<div class="insight-box">
        Rata-rata <b>{idle_pct:.1f}%</b> kapasitas kas ATM menganggur setiap saat (utilisasi hanya {avg_util:.1f}%)
        \u2014 dana idle ini yang mendasari peluang efisiensi biaya modal.</div>""", unsafe_allow_html=True)

    st.caption(
        f"Tipe lokasi berbiaya tertinggi: **{top_cost_loc['Location_Type']}** "
        f"({fmt_rp_jt(top_cost_loc['Annual_Cost'])}/tahun) \u2014 wajar mengikuti volume & kapasitas, "
        f"namun juga tempat peluang penghematan terbesar: **{top_savings_loc['Location_Type']}** "
        f"({fmt_rp_jt(top_savings_loc['Annual_Savings'])}/tahun)."
    )


# =====================================================================
# TAB 2 — BIAYA & UTILISASI
# =====================================================================
with tabs[1]:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">Komposisi Biaya: Holding vs Logistik</div>', unsafe_allow_html=True)
        comp_df = pd.DataFrame({
            "Komponen": ["Biaya Modal (Holding)", "Biaya Logistik (CIT)"],
            "Nilai": [total_holding_annual, total_logistics_annual],
        })
        fig = px.pie(comp_df, names="Komponen", values="Nilai", hole=0.55,
                     color_discrete_sequence=[NAVY, GOLD])
        fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>Rp%{value:,.0f}<extra></extra>")
        fig = style_fig(fig, height=380, legend_bottom=True)
        st.plotly_chart(fig, width="stretch")
        st.caption(
            f"Biaya modal (opportunity cost dana idle) menyumbang "
            f"**{total_holding_annual/total_cost_annual*100:.0f}%** dari total biaya operasional jaringan \u2014 "
            f"komponen terbesar yang dapat ditekan lewat right-sizing kuantitas isi ulang."
        )

    with c2:
        st.markdown('<div class="section-title">Utilisasi Kas Rata-Rata per ATM</div>', unsafe_allow_html=True)
        atm_u = atm_summary.sort_values("Util_Pct", ascending=True)
        fig2 = px.bar(atm_u, x="Util_Pct", y="ATM_ID", orientation="h", color="Location_Type",
                      color_discrete_sequence=CATEGORY_COLORS,
                      hover_data={"Util_Pct": ":.1f"})
        fig2.add_vline(x=avg_util, line_dash="dash", line_color=CORAL,
                        annotation_text=f"Rata2: {avg_util:.1f}%", annotation_font_color=CORAL)
        fig2 = style_fig(fig2, height=380)
        fig2.update_xaxes(title="Utilisasi (%)")
        fig2.update_yaxes(title=None)
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-title">Distribusi Utilisasi Kas Harian</div>', unsafe_allow_html=True)
    fig3 = px.histogram(df, x="Utilization_Pct", color="Location_Type", nbins=40,
                         color_discrete_sequence=CATEGORY_COLORS, opacity=0.75, barmode="overlay")
    fig3 = style_fig(fig3, height=340)
    fig3.update_xaxes(title="Utilisasi Harian (%)")
    fig3.update_yaxes(title="Jumlah Hari")
    st.plotly_chart(fig3, width="stretch")

    lowest_util = atm_summary.loc[atm_summary["Util_Pct"].idxmin()]
    highest_util = atm_summary.loc[atm_summary["Util_Pct"].idxmax()]
    st.markdown(f"""<div class="insight-box">
    Rentang utilisasi antar ATM cukup lebar: dari <b>{lowest_util['ATM_ID']}</b> ({lowest_util['Util_Pct']:.1f}%)
    hingga <b>{highest_util['ATM_ID']}</b> ({highest_util['Util_Pct']:.1f}%). Sebaran ini berguna untuk menargetkan
    ATM mana yang paling mendesak untuk di-right-size terlebih dahulu (lihat tab <b>Optimasi EOQ</b>).</div>""",
    unsafe_allow_html=True)


# =====================================================================
# TAB 3 — OPTIMASI EOQ
# =====================================================================
with tabs[2]:
    st.markdown('<div class="section-title">Model Economic Order Quantity (EOQ)</div>', unsafe_allow_html=True)
    fc1, fc2 = st.columns([1, 2])
    with fc1:
        st.latex(r"Q^{*} = \sqrt{\dfrac{2 \, D \, S}{H}}")
    with fc2:
        st.markdown(f"""<div class="insight-box">
        <b>D</b> = rata-rata penarikan harian &bull; <b>S</b> = biaya logistik per trip &bull;
        <b>H</b> = tingkat biaya modal harian (saat ini: <b>{holding_rate:.1f}%/tahun</b>, dapat diubah di sidebar).
        Kuantitas order dibatasi maksimum {capacity_cap*100:.0f}% dari kapasitas fisik ATM.</div>""",
        unsafe_allow_html=True)

    view_mode = st.radio("Tampilkan per:", ["Tipe Lokasi", "ATM Individual"], horizontal=True)

    if view_mode == "Tipe Lokasi":
        loc_sorted = loc_summary.sort_values("Annual_Savings", ascending=False)
        fig = px.bar(loc_sorted, x="Location_Type", y="Annual_Savings", color="Location_Type",
                     color_discrete_sequence=CATEGORY_COLORS, text_auto=".2s")
        fig.update_traces(hovertemplate="%{x}<br>Potensi Hemat: Rp%{y:,.0f}<extra></extra>", showlegend=False)
        fig = style_fig(fig, height=400)
        fig.update_yaxes(title="Potensi Hemat / Tahun (IDR)")
        fig.update_xaxes(title=None)
        st.plotly_chart(fig, width="stretch")
    else:
        atm_sorted = atm_summary.sort_values("Annual_Savings", ascending=True)
        fig = px.bar(atm_sorted, x="Annual_Savings", y="ATM_ID", orientation="h", color="Location_Type",
                     color_discrete_sequence=CATEGORY_COLORS)
        fig.update_traces(hovertemplate="%{y}<br>Potensi Hemat: Rp%{x:,.0f}<extra></extra>")
        fig = style_fig(fig, height=560)
        fig.update_xaxes(title="Potensi Hemat / Tahun (IDR)")
        fig.update_yaxes(title=None)
        st.plotly_chart(fig, width="stretch")

    st.markdown('<div class="section-title">Tabel Detail EOQ per ATM</div>', unsafe_allow_html=True)
    tbl = atm_summary.copy().sort_values("Annual_Savings", ascending=False)
    tbl_display = pd.DataFrame({
        "ATM": tbl["ATM_ID"],
        "Tipe Lokasi": tbl["Location_Type"],
        "Kapasitas": tbl["Max_Capacity"].map(lambda v: fmt_rp(v)),
        "Utilisasi": tbl["Util_Pct"].map(lambda v: fmt_pct(v)),
        "Qty Order Aktual": (tbl["Total_Replenishment"] / tbl["Trips"].replace(0, np.nan)).map(lambda v: fmt_rp(v)),
        "Qty EOQ Optimal": tbl["EOQ_Qty_Constrained"].map(lambda v: fmt_rp(v)),
        "Status EOQ": np.where(tbl["EOQ_Feasible"], "Berpeluang diperkecil", "Sudah optimal (dibatasi kapasitas)"),
        "Biaya Saat Ini/Thn": tbl["Annual_Cost_Current"].map(lambda v: fmt_rp(v)),
        "Potensi Hemat/Thn": tbl["Annual_Savings"].map(lambda v: fmt_rp(v)),
        "Hemat %": tbl["Savings_Pct"].map(lambda v: fmt_pct(v)),
    })
    st.dataframe(tbl_display, width="stretch", hide_index=True, height=380)

    csv_buf = io.StringIO()
    tbl.to_csv(csv_buf, index=False)
    st.download_button("\u2B07\uFE0F Unduh Tabel EOQ Lengkap (CSV)", data=csv_buf.getvalue(),
                        file_name="eoq_summary_per_atm.csv", mime="text/csv")

    n_feasible = int((~tbl["EOQ_Feasible"]).sum())
    n_reducible = int(tbl["EOQ_Feasible"].sum())
    st.markdown(f"""<div class="gold-box">
    Dari {len(tbl)} ATM pada filter saat ini: <b>{n_reducible} ATM</b> berpeluang menurunkan kuantitas
    isi ulang (EOQ &lt; kapasitas), sementara <b>{n_feasible} ATM</b> lainnya sudah berada pada kebijakan
    optimal karena EOQ hasil perhitungan justru melebihi kapasitas fisik mesin.</div>""", unsafe_allow_html=True)


# =====================================================================
# TAB 4 — VOLATILITAS & MUSIMAN
# =====================================================================
with tabs[3]:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">Koefisien Variasi (CV) Permintaan</div>', unsafe_allow_html=True)
        cv_sorted = loc_summary.sort_values("CV", ascending=False)
        fig = px.bar(cv_sorted, x="Location_Type", y="CV", color="CV",
                     color_continuous_scale=[ICE, GOLD, CORAL])
        fig.update_traces(hovertemplate="%{x}<br>CV: %{y:.3f}<extra></extra>", texttemplate="%{y:.2f}", textposition="outside")
        fig = style_fig(fig, height=380)
        fig.update_coloraxes(showscale=False)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title="CV (Std Dev / Rata-rata)")
        st.plotly_chart(fig, width="stretch")
        st.caption("CV = Std. Dev \u00F7 Rata-rata penarikan harian. Makin tinggi, makin sulit diprediksi.")

    with c2:
        st.markdown('<div class="section-title">Pola Hari Kerja vs Akhir Pekan</div>', unsafe_allow_html=True)
        wk_df = loc_summary[["Location_Type", "Weekday_Avg", "Weekend_Avg"]].melt(
            id_vars="Location_Type", var_name="Periode", value_name="Rata2 Penarikan")
        wk_df["Periode"] = wk_df["Periode"].map({"Weekday_Avg": "Hari Kerja", "Weekend_Avg": "Akhir Pekan"})
        fig2 = px.bar(wk_df, x="Location_Type", y="Rata2 Penarikan", color="Periode", barmode="group",
                      color_discrete_sequence=[NAVY, GOLD])
        fig2.update_traces(hovertemplate="%{x}<br>Rp%{y:,.0f}<extra></extra>")
        fig2 = style_fig(fig2, height=380)
        fig2.update_xaxes(title=None)
        st.plotly_chart(fig2, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="section-title">Rata-Rata Penarikan per Hari</div>', unsafe_allow_html=True)
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_id = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu", "Thursday": "Kamis",
                  "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}
        dow = df.groupby("Day_Name")["Actual_Withdrawal_IDR"].mean().reindex(dow_order).reset_index()
        dow["Hari"] = dow["Day_Name"].map(dow_id)
        colors_dow = [CORAL if d in ("Saturday", "Sunday") else NAVY for d in dow["Day_Name"]]
        fig3 = go.Figure(go.Bar(x=dow["Hari"], y=dow["Actual_Withdrawal_IDR"], marker_color=colors_dow,
                                 hovertemplate="%{x}<br>Rp%{y:,.0f}<extra></extra>"))
        fig3 = style_fig(fig3, height=330)
        fig3.update_yaxes(title="Rata2 Penarikan")
        st.plotly_chart(fig3, width="stretch")

    with c4:
        st.markdown('<div class="section-title">Tren Bulanan per Tipe Lokasi</div>', unsafe_allow_html=True)
        monthly_loc = df.groupby(["Month", "Location_Type"])["Actual_Withdrawal_IDR"].sum().reset_index()
        fig4 = px.line(monthly_loc, x="Month", y="Actual_Withdrawal_IDR", color="Location_Type",
                       color_discrete_sequence=CATEGORY_COLORS, markers=True)
        fig4 = style_fig(fig4, height=330)
        fig4.update_yaxes(title=None)
        fig4.update_xaxes(title=None)
        st.plotly_chart(fig4, width="stretch")

    most_volatile = loc_summary.loc[loc_summary["CV"].idxmax()]
    most_weekend = loc_summary.loc[loc_summary["Weekend_Uplift_Pct"].idxmax()]
    most_weekday = loc_summary.loc[loc_summary["Weekend_Uplift_Pct"].idxmin()]
    st.markdown(f"""<div class="risk-box">
    <b>{most_volatile['Location_Type']}</b> memiliki volatilitas permintaan tertinggi (CV={most_volatile['CV']:.2f}) \u2014
    perlu buffer & pemantauan lebih ketat. Pola akhir pekan juga berlawanan arah:
    <b>{most_weekend['Location_Type']}</b> naik {most_weekend['Weekend_Uplift_Pct']:+.0f}% saat akhir pekan,
    sedangkan <b>{most_weekday['Location_Type']}</b> turun {most_weekday['Weekend_Uplift_Pct']:+.0f}%.
    Sinkronisasi jadwal CIT dengan pola ini dapat menekan risiko sekaligus trip logistik yang sia-sia.</div>""",
    unsafe_allow_html=True)


# =====================================================================
# TAB 5 — WILAYAH & LOGISTIK
# =====================================================================
with tabs[4]:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">Total Biaya Operasional per Wilayah</div>', unsafe_allow_html=True)
        reg_sorted = region_summary.sort_values("Annual_Cost", ascending=True)
        fig = px.bar(reg_sorted, x="Annual_Cost", y="Region", orientation="h", color="ATMs",
                     color_continuous_scale=[ICE, NAVY], text=reg_sorted["ATMs"].map(lambda v: f"{v} ATM"))
        fig.update_traces(hovertemplate="%{y}<br>Rp%{x:,.0f}<extra></extra>", textposition="outside")
        fig = style_fig(fig, height=380)
        fig.update_xaxes(title="Biaya / Tahun (IDR)")
        fig.update_yaxes(title=None)
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown('<div class="section-title">Biaya Logistik (CIT) per Trip</div>', unsafe_allow_html=True)
        trip_sorted = loc_summary.sort_values("Avg_Logistics_per_Trip", ascending=False)
        fig2 = px.bar(trip_sorted, x="Location_Type", y="Avg_Logistics_per_Trip", color="Location_Type",
                      color_discrete_sequence=CATEGORY_COLORS)
        fig2.update_traces(hovertemplate="%{x}<br>Rp%{y:,.0f}/trip<extra></extra>", showlegend=False)
        fig2 = style_fig(fig2, height=380)
        fig2.update_xaxes(title=None)
        fig2.update_yaxes(title="Rata2 Biaya/Trip (IDR)")
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-title">Peta Komposisi Biaya: Wilayah \u00D7 Tipe Lokasi</div>', unsafe_allow_html=True)
    tree = df.groupby(["Region", "Location_Type"]).agg(
        Total_Cost=("Holding_Cost_IDR", lambda x: x.sum()),
    ).reset_index()
    tree2 = df.groupby(["Region", "Location_Type"])[["Holding_Cost_IDR", "Logistics_Cost_IDR"]].sum().reset_index()
    tree2["Total_Cost"] = tree2["Holding_Cost_IDR"] + tree2["Logistics_Cost_IDR"]
    fig3 = px.treemap(tree2, path=["Region", "Location_Type"], values="Total_Cost",
                       color="Total_Cost", color_continuous_scale=[ICE, GOLD, NAVY])
    fig3.update_traces(hovertemplate="%{label}<br>Rp%{value:,.0f}<extra></extra>")
    fig3 = style_fig(fig3, height=420, legend_bottom=False)
    fig3.update_coloraxes(showscale=False)
    st.plotly_chart(fig3, width="stretch")

    top_region = region_summary.loc[region_summary["Annual_Cost"].idxmax()]
    trip_hi = loc_summary.loc[loc_summary["Avg_Logistics_per_Trip"].idxmax()]
    trip_lo = loc_summary.loc[loc_summary["Avg_Logistics_per_Trip"].idxmin()]
    gap_pct = (trip_hi["Avg_Logistics_per_Trip"] / trip_lo["Avg_Logistics_per_Trip"] - 1) * 100
    st.markdown(f"""<div class="gold-box">
    <b>{top_region['Region']}</b> menanggung biaya operasional tertinggi ({fmt_rp_jt(top_region['Annual_Cost'])}/tahun,
    {int(top_region['ATMs'])} ATM). Sementara itu, biaya logistik per trip <b>{trip_hi['Location_Type']}</b>
    ({fmt_rp(trip_hi['Avg_Logistics_per_Trip'])}) lebih mahal <b>{gap_pct:.0f}%</b> dibanding
    <b>{trip_lo['Location_Type']}</b> ({fmt_rp(trip_lo['Avg_Logistics_per_Trip'])}) \u2014 layak menjadi
    bahan review kontrak & rute vendor CIT.</div>""", unsafe_allow_html=True)


# =====================================================================
# TAB 6 — KEBIJAKAN REPLENISHMENT
# =====================================================================
with tabs[5]:
    repl = df[df["Is_Replenishment"]].copy()

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Event Isi Ulang", fmt_num(len(repl)))
    k2.metric("Insiden Stockout", f"{stockout_days}", delta="Aman" if stockout_days == 0 else "Perlu perhatian",
              delta_color="normal" if stockout_days == 0 else "inverse")
    k3.metric("Rata2 Trigger Isi Ulang", fmt_pct(repl["PreRefill_Pct"].mean()) if len(repl) else "-")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">Sebaran Level Trigger Isi Ulang (% Kapasitas)</div>', unsafe_allow_html=True)
        if len(repl):
            fig = px.box(repl, x="Location_Type", y="PreRefill_Pct", color="Location_Type",
                         color_discrete_sequence=CATEGORY_COLORS, points="outliers")
            fig.update_traces(showlegend=False)
            fig = style_fig(fig, height=380)
            fig.update_xaxes(title=None)
            fig.update_yaxes(title="Level Kas Saat Trigger (%)")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Tidak ada event isi ulang pada filter saat ini.")

    with c2:
        st.markdown('<div class="section-title">Rata-Rata Siklus Isi Ulang per ATM (Hari)</div>', unsafe_allow_html=True)
        cyc = atm_summary.dropna(subset=["Avg_Cycle_Days"]).sort_values("Avg_Cycle_Days", ascending=True)
        fig2 = px.bar(cyc, x="Avg_Cycle_Days", y="ATM_ID", orientation="h", color="Location_Type",
                      color_discrete_sequence=CATEGORY_COLORS)
        fig2.update_traces(hovertemplate="%{y}<br>%{x:.1f} hari<extra></extra>")
        fig2 = style_fig(fig2, height=380)
        fig2.update_xaxes(title="Hari")
        fig2.update_yaxes(title=None)
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-title">Perbandingan Kebijakan Aktual vs EOQ per Tipe Lokasi</div>', unsafe_allow_html=True)
    policy_tbl = pd.DataFrame({
        "Tipe Lokasi": loc_summary["Location_Type"],
        "Rata2 Trigger Isi Ulang": repl.groupby("Location_Type")["PreRefill_Pct"].mean().reindex(loc_summary["Location_Type"]).values,
        "Rata2 Siklus Aktual (hari)": atm_summary.groupby("Location_Type")["Avg_Cycle_Days"].mean().reindex(loc_summary["Location_Type"]).values,
        "Rata2 Siklus EOQ (hari)": atm_summary.groupby("Location_Type")["EOQ_Cycle_Days"].mean().reindex(loc_summary["Location_Type"]).values,
        "CV Demand": loc_summary["CV"].values,
    })
    policy_tbl["Rekomendasi Buffer"] = np.where(
        policy_tbl["CV Demand"] > 0.4, "Pertahankan / perketat (volatilitas tinggi)",
        np.where(policy_tbl["CV Demand"] > 0.3, "Pertahankan (volatilitas sedang)", "Dapat ditipiskan (volatilitas rendah)")
    )
    disp = policy_tbl.copy()
    disp["Rata2 Trigger Isi Ulang"] = disp["Rata2 Trigger Isi Ulang"].map(lambda v: fmt_pct(v) if pd.notna(v) else "-")
    disp["Rata2 Siklus Aktual (hari)"] = disp["Rata2 Siklus Aktual (hari)"].map(lambda v: f"{v:.1f}" if pd.notna(v) else "-")
    disp["Rata2 Siklus EOQ (hari)"] = disp["Rata2 Siklus EOQ (hari)"].map(lambda v: f"{v:.1f}" if pd.notna(v) else "-")
    disp["CV Demand"] = disp["CV Demand"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "-")
    st.dataframe(disp, width="stretch", hide_index=True)

    if stockout_days == 0 and len(repl):
        st.markdown(f"""<div class="insight-box">
        <b>Nol stockout</b> tercatat sepanjang {len(repl)} event isi ulang pada filter saat ini, dengan trigger
        rata-rata {fmt_pct(repl['PreRefill_Pct'].mean())} dari kapasitas. Ini mengindikasikan buffer yang relatif
        konservatif \u2014 berpotensi diturunkan secara terkendali (pilot) khususnya pada tipe lokasi dengan CV rendah,
        dengan pemantauan ketat agar Stockout_Penalty_Cost_IDR tetap nol.</div>""", unsafe_allow_html=True)
    elif stockout_days > 0:
        st.markdown(f"""<div class="risk-box">
        Tercatat <b>{stockout_days} hari stockout</b> pada filter saat ini. Perlu investigasi ATM & periode
        terkait sebelum mempertimbangkan penurunan buffer lebih lanjut.</div>""", unsafe_allow_html=True)


# =====================================================================
# TAB 7 — REKOMENDASI (dihasilkan otomatis dari data terfilter saat ini)
# =====================================================================
with tabs[6]:
    st.markdown('<div class="section-title">Rekomendasi Kebijakan \u2014 Dihasilkan dari Data Terfilter</div>', unsafe_allow_html=True)
    st.caption("Angka di bawah menyesuaikan otomatis dengan filter & asumsi yang dipilih di sidebar.")

    top2 = loc_summary.nlargest(2, "Annual_Savings")
    top2_names = " & ".join(top2["Location_Type"].tolist())
    top2_share = top2["Annual_Savings"].sum() / max(total_savings, 1e-9) * 100
    low_cv = loc_summary.nsmallest(2, "CV")["Location_Type"].tolist()
    high_cv_row = loc_summary.loc[loc_summary["CV"].idxmax()]
    weekend_up = loc_summary.loc[loc_summary["Weekend_Uplift_Pct"].idxmax()]
    weekend_down = loc_summary.loc[loc_summary["Weekend_Uplift_Pct"].idxmin()]
    trip_hi = loc_summary.loc[loc_summary["Avg_Logistics_per_Trip"].idxmax()]
    trip_lo = loc_summary.loc[loc_summary["Avg_Logistics_per_Trip"].idxmin()]

    recs = [
        ("1", "Right-Size Kuantitas Isi Ulang (EOQ)",
         f"Estimasi potensi penghematan **{fmt_rp_jt(total_savings)}/tahun ({savings_pct:.1f}%)** dengan menurunkan "
         f"target isi dari kapasitas penuh ke kuantitas EOQ optimal. Prioritaskan **{top2_names}** "
         f"yang menyumbang **{top2_share:.0f}%** dari total peluang penghematan (lihat tab Optimasi EOQ)."),
        ("2", "Diferensiasi Buffer per Profil Volatilitas",
         f"**{high_cv_row['Location_Type']}** memiliki volatilitas tertinggi (CV={high_cv_row['CV']:.2f}) dan "
         f"memerlukan buffer & pemantauan lebih ketat. Sebaliknya, **{', '.join(low_cv)}** memiliki permintaan "
         f"paling stabil \u2014 kandidat ideal untuk buffer lebih tipis & siklus isi ulang lebih panjang."),
        ("3", "Penjadwalan CIT Berbasis Pola Weekday/Weekend",
         f"**{weekend_up['Location_Type']}** naik {weekend_up['Weekend_Uplift_Pct']:+.0f}% saat akhir pekan \u2014 "
         f"top-up sebelum akhir pekan. **{weekend_down['Location_Type']}** turun {weekend_down['Weekend_Uplift_Pct']:+.0f}% "
         f"\u2014 hindari top-up akhir pekan yang tidak perlu."),
        ("4", "Review Kontrak & Rute Vendor CIT",
         f"Biaya logistik per trip **{trip_hi['Location_Type']}** ({fmt_rp(trip_hi['Avg_Logistics_per_Trip'])}) "
         f"lebih mahal dibanding **{trip_lo['Location_Type']}** ({fmt_rp(trip_lo['Avg_Logistics_per_Trip'])}) \u2014 "
         f"layak menjadi bahan renegosiasi kontrak/konsolidasi rute vendor CIT."),
        ("5", "Perbaiki Efisiensi Kapital / Neraca",
         f"Rata-rata **{100-avg_util:.1f}%** kapasitas kas ATM menganggur setiap saat (utilisasi hanya {avg_util:.1f}%). "
         f"Menurunkan target isi ulang (Rekomendasi #1) langsung menekan opportunity cost dana idle ini."),
        ("6", "Pilot Penurunan Reorder Threshold",
         f"Dengan {stockout_days} insiden stockout tercatat pada {int(atm_summary['Trips'].sum())} event isi ulang, "
         f"pertimbangkan pilot penurunan threshold trigger secara terkendali pada ATM ber-CV rendah, dengan "
         f"pemantauan ketat agar Stockout_Penalty_Cost_IDR tetap nol."),
    ]

    for num, title, body in recs:
        st.markdown(f"""<div class="rec-card">
        <span class="rec-num">{num}</span><b style="color:{NAVY}; font-size:1.02rem;">{title}</b>
        <p style="margin:0.5rem 0 0 2.4rem; color:{SLATE}; font-size:0.93rem; line-height:1.5;">{body}</p>
        </div>""", unsafe_allow_html=True)


# =====================================================================
# TAB 8 — DATA EXPLORER
# =====================================================================
with tabs[7]:
    st.markdown('<div class="section-title">Jelajahi Data Mentah (Sesuai Filter Aktif)</div>', unsafe_allow_html=True)
    st.caption(f"Menampilkan {len(df):,} baris dari {df['ATM_ID'].nunique()} ATM, {period_str}.".replace(",", "."))

    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        show_atm = st.multiselect("Filter tambahan: ATM", sorted(df["ATM_ID"].unique()), default=[], key="explorer_atm")
    with ec2:
        search_col = st.selectbox("Urutkan berdasarkan", ["Log_Date", "ATM_ID", "Actual_Withdrawal_IDR", "Holding_Cost_IDR", "Logistics_Cost_IDR"])
    with ec3:
        sort_desc = st.checkbox("Urutan menurun", value=True)

    df_show = df[df["ATM_ID"].isin(show_atm)] if show_atm else df
    df_show = df_show.sort_values(search_col, ascending=not sort_desc)

    display_cols = ["Log_Date", "ATM_ID", "Location_Type", "Region", "Max_Capacity_IDR",
                     "Beginning_Cash_IDR", "Replenishment_Amount_IDR", "Actual_Withdrawal_IDR",
                     "Ending_Cash_IDR", "Is_Stockout", "Holding_Cost_IDR", "Logistics_Cost_IDR"]
    st.dataframe(df_show[display_cols], width="stretch", hide_index=True, height=420)

    dl1, dl2 = st.columns(2)
    with dl1:
        csv_full = df_show[display_cols].to_csv(index=False)
        st.download_button("\u2B07\uFE0F Unduh Data Terfilter (CSV)", data=csv_full,
                            file_name="atm_data_filtered.csv", mime="text/csv", width="stretch")
    with dl2:
        csv_atm_summary = atm_summary.to_csv(index=False)
        st.download_button("\u2B07\uFE0F Unduh Ringkasan per ATM (CSV)", data=csv_atm_summary,
                            file_name="atm_summary_computed.csv", mime="text/csv", width="stretch")

    with st.expander("\U0001F4C8 Statistik Deskriptif (kolom numerik)"):
        st.dataframe(df_show[["Max_Capacity_IDR", "Beginning_Cash_IDR", "Actual_Withdrawal_IDR",
                               "Holding_Cost_IDR", "Logistics_Cost_IDR"]].describe().round(1), width="stretch")
