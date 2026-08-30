import calendar
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Trading Dashboard", layout="wide")
TZ = "America/New_York"

sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

if "session" not in st.session_state:
    st.title("Sign in")
    email = st.text_input("Email")
    pw = st.text_input("Password", type="password")
    if st.button("Sign in"):
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": pw})
            st.session_state.session = res.session
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")
    st.stop()

sb.postgrest.auth(st.session_state.session.access_token)
if st.sidebar.button("Sign out"):
    del st.session_state.session
    st.rerun()


@st.cache_data(ttl=120)
def load(token):
    sb.postgrest.auth(token)
    acct = pd.DataFrame(sb.table("accounts").select("*").execute().data)
    deals = pd.DataFrame(sb.table("deals").select("*").order("time").limit(100000).execute().data)
    snaps = pd.DataFrame(sb.table("snapshots").select("*").order("time", desc=True).limit(1).execute().data)
    pos = pd.DataFrame(sb.table("positions").select("*").execute().data)
    return acct, deals, snaps, pos


acct, deals, snaps, pos = load(st.session_state.session.access_token)
if deals.empty:
    st.warning("No deals yet - is the collector running on the VPS?")
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

st.title(f"{a.get('name', '')}  -  {a.get('login', '')}")
st.caption(f"{a.get('broker', '')} - {a.get('server', '')} - leverage {a.get('leverage', '')}")


def card(col, label, value):
    col.metric(label, value)


c = st.columns(7)
card(c[0], "Balance", f"{balance:,.2f}")
card(c[1], "Equity", f"{equity:,.2f}")
card(c[2], "Floating P&L", f"{floating:,.2f}")
card(c[3], "Growth %", f"{(total_profit / deposits * 100) if deposits else 0:.2f}%")
card(c[4], "Total Profit", f"{total_profit:,.2f}")
card(c[5], "Deposits", f"{deposits:,.2f}")
card(c[6], "Withdrawals", f"{withdrawals:,.2f}")

today = datetime.now(pd.Timestamp.now(TZ).tz).date()
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)
daily = trades.groupby("date")["net"].sum()
c = st.columns(3)
card(c[0], "Daily Profit", f"{daily.get(today, 0):,.2f}")
card(c[1], "Weekly Profit", f"{daily[daily.index >= week_start].sum():,.2f}")
card(c[2], "Monthly Profit", f"{daily[daily.index >= month_start].sum():,.2f}")

st.subheader("Profit/Loss Over Time")
curve = trades.groupby("date")["net"].sum().cumsum().reset_index()
fig = go.Figure(go.Scatter(x=curve["date"], y=curve["net"], mode="lines", fill="tozeroy"))
fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Cumulative P&L")
st.plotly_chart(fig, use_container_width=True)

wins = trades[trades["net"] > 0]
losses = trades[trades["net"] < 0]
n = len(trades)
c = st.columns(8)
card(c[0], "Trades", f"{n:,}")
card(c[1], "Win %", f"{len(wins) / n * 100 if n else 0:.0f}%")
card(c[2], "Longs / Shorts", f"{(trades['direction'] == 'Long').sum():,} / {(trades['direction'] == 'Short').sum():,}")
card(c[3], "Avg Win", f"{wins['net'].mean() if len(wins) else 0:,.2f}")
card(c[4], "Avg Loss", f"{losses['net'].mean() if len(losses) else 0:,.2f}")
card(c[5], "Best", f"{trades['net'].max():,.2f}")
card(c[6], "Worst", f"{trades['net'].min():,.2f}")
card(c[7], "RRR", f"{(wins['net'].mean() / abs(losses['net'].mean())) if len(wins) and len(losses) else 0:.2f}")

st.subheader("Trading Calendar")
months = sorted({(d.year, d.month) for d in trades["date"]}, reverse=True)
ym = st.selectbox("Month", months, format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}")
year, month = ym
first = date(year, month, 1)
start_bal = deals.loc[deals["date"] < first, "balance"].iloc[-1] if (deals["date"] < first).any() else deposits
month_daily = daily[[d.year == year and d.month == month for d in daily.index]]
st.markdown(f"**{calendar.month_name[month]} - {month_daily.sum():+,.2f} ({month_daily.sum() / start_bal * 100 if start_bal else 0:+.2f}%)**")

cols = st.columns(7)
for i, name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
    cols[i].markdown(f"<div style='text-align:center;color:#888'>{name}</div>", unsafe_allow_html=True)
cal = calendar.Calendar(firstweekday=6)
for week in cal.monthdayscalendar(year, month):
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].markdown("&nbsp;", unsafe_allow_html=True)
            continue
        d = date(year, month, day)
        val = month_daily.get(d)
        if val is None:
            bg, body = "#1e2230", ""
        else:
            bg = "#1f5a45" if val >= 0 else "#6a2a2a"
            body = f"<br><b>${val:,.2f}</b><br><small>{val / start_bal * 100 if start_bal else 0:+.2f}%</small>"
        cols[i].markdown(
            f"<div style='background:{bg};border-radius:8px;padding:12px;text-align:center;"
            f"min-height:80px;margin-bottom:6px'>{day}{body}</div>", unsafe_allow_html=True)

left, right = st.columns([1, 2])
with left:
    st.subheader("Symbols Traded")
    sym = trades["symbol"].value_counts().reset_index()
    sym.columns = ["symbol", "trades"]
    st.plotly_chart(px.pie(sym, names="symbol", values="trades", hole=0.5).update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0)), use_container_width=True)
with right:
    st.subheader("Monthly Growth")
    m = trades.copy()
    m["month"] = m["time"].dt.to_period("M").astype(str)
    mg = m.groupby("month")["net"].sum().reset_index()
    st.plotly_chart(px.bar(mg, x="month", y="net").update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0)), use_container_width=True)

tab_open, tab_closed = st.tabs(["Open", "Closed"])
with tab_open:
    if pos.empty:
        st.info("No open positions.")
    else:
        pos["type"] = pos["type"].map({0: "Buy", 1: "Sell"})
        st.dataframe(pos[["ticket", "time", "type", "symbol", "volume", "price_open", "price_current", "sl", "tp", "swap", "profit", "comment"]], use_container_width=True, hide_index=True)
with tab_closed:
    show = trades.sort_values("time", ascending=False)[["ticket", "time", "direction", "symbol", "volume", "price", "commission", "swap", "profit", "net", "comment"]]
    st.dataframe(show.head(500), use_container_width=True, hide_index=True)
