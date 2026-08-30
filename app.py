import calendar
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Kona Wolf Trading", page_icon="📈", layout="wide")
TZ = "America/New_York"

# ---------------------------------------------------------------- palette
BG, CARD, LINE = "#0B1220", "#121A2B", "#1E2A40"
TEXT, MUTED, ACCENT = "#E6EBF5", "#8A94A8", "#F0B429"
GREEN, RED, BLUE = "#2FBF71", "#E5484D", "#5B9CF6"
SYMBOL_COLORS = ["#5B9CF6", "#F0B429", "#2FBF71", "#E5484D", "#A78BFA", "#F97316",
                 "#22D3EE", "#F472B6", "#84CC16", "#FB7185", "#38BDF8", "#FBBF24",
                 "#34D399", "#C084FC", "#94A3B8"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }}
.kw-head {{ display:flex; align-items:baseline; gap:14px; margin-bottom:4px; }}
.kw-title {{ font-size:26px; font-weight:600; color:{TEXT}; letter-spacing:-0.01em; }}
.kw-acct {{ font-family:'IBM Plex Mono', monospace; color:{ACCENT}; font-size:15px; }}
.kw-sub {{ color:{MUTED}; font-size:13px; margin-bottom:22px; }}
.kw-card {{ background:{CARD}; border:1px solid {LINE}; border-radius:10px; padding:14px 16px 12px; margin-bottom:12px; }}
.kw-label {{ color:{MUTED}; font-size:11px; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:6px; }}
.kw-value {{ font-family:'IBM Plex Mono', monospace; font-size:22px; font-weight:600; color:{TEXT}; }}
.kw-value.pos {{ color:{GREEN}; }}  .kw-value.neg {{ color:{RED}; }}
.kw-section {{ font-size:15px; font-weight:600; color:{TEXT}; margin:26px 0 10px; }}
.kw-dow {{ text-align:center; color:{MUTED}; font-size:11px; letter-spacing:0.08em; text-transform:uppercase; padding-bottom:6px; }}
.kw-day {{ border-radius:8px; padding:10px 8px; min-height:86px; margin-bottom:8px; text-align:center;
           font-family:'IBM Plex Mono', monospace; border:1px solid {LINE}; }}
.kw-day .n {{ font-size:12px; color:{MUTED}; }}
.kw-day .v {{ font-size:15px; font-weight:600; margin-top:6px; }}
.kw-day .p {{ font-size:11px; opacity:0.8; }}
.kw-day.pos {{ background:#12352A; border-color:#1F5A45; color:{GREEN}; }}
.kw-day.neg {{ background:#3A1B1F; border-color:#6A2A2A; color:{RED}; }}
.kw-day.flat {{ background:{CARD}; color:{TEXT}; }}
.kw-day.empty {{ background:transparent; border-color:transparent; }}
.kw-monthline {{ font-family:'IBM Plex Mono', monospace; font-size:16px; margin-bottom:10px; }}
div[data-testid="stSidebar"] {{ background:{CARD}; border-right:1px solid {LINE}; }}
</style>
""", unsafe_allow_html=True)

sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

# ---------------------------------------------------------------- login
if "session" not in st.session_state:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(f"<div class='kw-head'><span class='kw-title'>Kona Wolf Trading</span></div>"
                    f"<div class='kw-sub'>Sign in to view the account</div>", unsafe_allow_html=True)
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Sign in", use_container_width=True):
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.session = res.session
                st.rerun()
            except Exception:
                st.error("Email or password didn't match.")
    st.stop()

sb.postgrest.auth(st.session_state.session.access_token)


# ---------------------------------------------------------------- data
@st.cache_data(ttl=120)
def load(token):
    sb.postgrest.auth(token)
    acct = pd.DataFrame(sb.table("accounts").select("*").execute().data)
    rows, start = [], 0
    while True:
        page = sb.table("deals").select("*").order("time").range(start, start + 999).execute().data
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    deals = pd.DataFrame(rows)
    snaps = pd.DataFrame(sb.table("snapshots").select("*").order("time", desc=True).limit(1).execute().data)
    pos = pd.DataFrame(sb.table("positions").select("*").execute().data)
    return acct, deals, snaps, pos


acct, deals, snaps, pos = load(st.session_state.session.access_token)
if deals.empty:
    st.warning("No trades yet. Check that the collector is running on the VPS.")
    st.stop()

deals["time"] = pd.to_datetime(deals["time"], utc=True).dt.tz_convert(TZ)
deals["net"] = deals["profit"].fillna(0) + deals["commission"].fillna(0) + deals["swap"].fillna(0)
deals["date"] = deals["time"].dt.date
deals["balance"] = deals["net"].cumsum()

trades = deals[deals["entry"].isin([1, 3]) & deals["type"].isin([0, 1])].copy()
trades["direction"] = trades["type"].map({1: "Long", 0: "Short"})
cash = deals[deals["type"] == 2]
deposits = cash.loc[cash["net"] > 0, "net"].sum()
withdrawals = cash.loc[cash["net"] < 0, "net"].sum()

a = acct.iloc[0] if not acct.empty else {}
s = snaps.iloc[0] if not snaps.empty else {}
balance = s.get("balance", deals["balance"].iloc[-1])
equity = s.get("equity", balance)
floating = s.get("floating_pl", 0)
total_profit = trades["net"].sum()
wins = trades[trades["net"] > 0]
losses = trades[trades["net"] < 0]
daily = trades.groupby("date")["net"].sum()
last_sync = pd.to_datetime(s["time"]).tz_convert(TZ).strftime("%b %d, %I:%M %p") if "time" in s else "—"

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<div class='kw-label'>Signed in</div><div style='font-size:13px;color:{TEXT}'>"
                f"{st.session_state.session.user.email}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kw-label' style='margin-top:14px'>Last sync</div>"
                f"<div style='font-size:13px;color:{TEXT}'>{last_sync}</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    months = sorted({(d.year, d.month) for d in trades["date"]}, reverse=True)
    ym = st.selectbox("Calendar month", months, format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}")
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        del st.session_state.session
        st.rerun()


# ---------------------------------------------------------------- helpers
def money(v):
    return f"{v:,.2f}"


def card(col, label, value, signed=None):
    cls = ""
    if signed is not None:
        cls = "pos" if signed > 0 else ("neg" if signed < 0 else "")
    col.markdown(f"<div class='kw-card'><div class='kw-label'>{label}</div>"
                 f"<div class='kw-value {cls}'>{value}</div></div>", unsafe_allow_html=True)


def section(title):
    st.markdown(f"<div class='kw-section'>{title}</div>", unsafe_allow_html=True)


def chart_layout(fig, height):
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor=CARD, plot_bgcolor=CARD,
                      font=dict(family="IBM Plex Sans", color=MUTED, size=12),
                      xaxis=dict(gridcolor=LINE, zerolinecolor=LINE), yaxis=dict(gridcolor=LINE, zerolinecolor=LINE),
                      showlegend=False)
    return fig


# ---------------------------------------------------------------- header
st.markdown(f"<div class='kw-head'><span class='kw-title'>{a.get('name', 'Account')}</span>"
            f"<span class='kw-acct'>#{a.get('login', '')}</span></div>"
            f"<div class='kw-sub'>{a.get('broker', '')} · {a.get('server', '')} · 1:{a.get('leverage', '')} · {a.get('currency', '')}</div>",
            unsafe_allow_html=True)

c = st.columns(4)
card(c[0], "Balance", money(balance))
card(c[1], "Equity", money(equity))
card(c[2], "Floating P&L", money(floating), floating)
card(c[3], "Total profit", money(total_profit), total_profit)

today = datetime.now(pd.Timestamp.now(TZ).tz).date()
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)
d_today = daily.get(today, 0)
d_week = daily[daily.index >= week_start].sum()
d_month = daily[daily.index >= month_start].sum()
c = st.columns(4)
card(c[0], "Today", money(d_today), d_today)
card(c[1], "This week", money(d_week), d_week)
card(c[2], "This month", money(d_month), d_month)
card(c[3], "Net deposits", money(deposits + withdrawals))

# ---------------------------------------------------------------- equity curve
section("Profit over time")
curve = daily.cumsum().reset_index()
curve.columns = ["date", "net"]
fig = go.Figure(go.Scatter(x=curve["date"], y=curve["net"], mode="lines",
                           line=dict(color=BLUE, width=2), fill="tozeroy", fillcolor="rgba(91,156,246,0.12)",
                           hovertemplate="%{x|%b %d}<br>%{y:,.0f}<extra></extra>"))
st.plotly_chart(chart_layout(fig, 340), use_container_width=True)

# ---------------------------------------------------------------- stats
section("Statistics")
n = len(trades)
c = st.columns(4)
card(c[0], "Trades", f"{n:,}")
card(c[1], "Win rate", f"{len(wins) / n * 100 if n else 0:.0f}%")
card(c[2], "Won / lost", f"{len(wins):,} / {len(losses):,}")
card(c[3], "Long / short", f"{(trades['direction'] == 'Long').sum():,} / {(trades['direction'] == 'Short').sum():,}")
c = st.columns(4)
aw = wins["net"].mean() if len(wins) else 0
al = losses["net"].mean() if len(losses) else 0
card(c[0], "Avg win", money(aw), 1)
card(c[1], "Avg loss", money(al), -1)
card(c[2], "Best / worst", f"{trades['net'].max():,.0f} / {trades['net'].min():,.0f}")
card(c[3], "Reward : risk", f"{(aw / abs(al)) if al else 0:.2f}")

# ---------------------------------------------------------------- calendar
year, month = ym
section(f"{calendar.month_name[month]} {year}")
first = date(year, month, 1)
start_bal = deals.loc[deals["date"] < first, "balance"].iloc[-1] if (deals["date"] < first).any() else deposits
month_daily = daily[[d.year == year and d.month == month for d in daily.index]]
m_total = month_daily.sum()
m_pct = m_total / start_bal * 100 if start_bal else 0
col = GREEN if m_total >= 0 else RED
st.markdown(f"<div class='kw-monthline' style='color:{col}'>{m_total:+,.2f} &nbsp;<span style='opacity:0.7'>({m_pct:+.2f}%)</span></div>",
            unsafe_allow_html=True)

cols = st.columns(7)
for i, name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
    cols[i].markdown(f"<div class='kw-dow'>{name}</div>", unsafe_allow_html=True)
for week in calendar.Calendar(firstweekday=6).monthdayscalendar(year, month):
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].markdown("<div class='kw-day empty'></div>", unsafe_allow_html=True)
            continue
        val = month_daily.get(date(year, month, day))
        if val is None:
            cols[i].markdown(f"<div class='kw-day flat'><div class='n'>{day}</div></div>", unsafe_allow_html=True)
        else:
            cls = "pos" if val >= 0 else "neg"
            pct = val / start_bal * 100 if start_bal else 0
            cols[i].markdown(f"<div class='kw-day {cls}'><div class='n'>{day}</div>"
                             f"<div class='v'>{val:+,.0f}</div><div class='p'>{pct:+.2f}%</div></div>",
                             unsafe_allow_html=True)

# ---------------------------------------------------------------- symbols + monthly
left, right = st.columns([1, 2])
with left:
    section("Symbols")
    sym = trades.groupby("symbol")["net"].agg(["count", "sum"]).reset_index().sort_values("count", ascending=False)
    fig = px.pie(sym, names="symbol", values="count", hole=0.62, color_discrete_sequence=SYMBOL_COLORS)
    fig.update_traces(textposition="outside", textinfo="label", marker=dict(line=dict(color=CARD, width=2)),
                      hovertemplate="%{label}<br>%{value} trades<extra></extra>")
    st.plotly_chart(chart_layout(fig, 340), use_container_width=True)
with right:
    section("Monthly profit")
    m = trades.copy()
    m["month"] = m["time"].dt.strftime("%b %Y")
    m["order"] = m["time"].dt.to_period("M")
    mg = m.groupby(["order", "month"])["net"].sum().reset_index().sort_values("order")
    fig = go.Figure(go.Bar(x=mg["month"], y=mg["net"], marker_color=[GREEN if v >= 0 else RED for v in mg["net"]],
                           hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    st.plotly_chart(chart_layout(fig, 340), use_container_width=True)

# ---------------------------------------------------------------- tables
section("Trades")
tab_open, tab_closed = st.tabs(["Open", "Closed"])
with tab_open:
    if pos.empty:
        st.caption("No open positions.")
    else:
        pos["type"] = pos["type"].map({0: "Buy", 1: "Sell"})
        st.dataframe(pos[["ticket", "time", "type", "symbol", "volume", "price_open", "price_current", "sl", "tp", "swap", "profit", "comment"]],
                     use_container_width=True, hide_index=True)
with tab_closed:
    show = trades.sort_values("time", ascending=False)[["ticket", "time", "direction", "symbol", "volume", "price", "commission", "swap", "profit", "net", "comment"]]
    show["time"] = show["time"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(show.head(500), use_container_width=True, hide_index=True)
