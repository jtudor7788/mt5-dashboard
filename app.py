import calendar
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Kona Wolf Trading", page_icon="📈", layout="wide")

DAY_TZ = "America/New_York"   # clock that decides which day/week a trade belongs to
BASE = 50000                  # each account trades on this; everything above is swept Friday

# ---------------------------------------------------------------- palette
CARD, LINE = "#121A2B", "#1E2A40"
TEXT, MUTED, ACCENT = "#E6EBF5", "#8A94A8", "#F0B429"
GREEN, RED, BLUE, PURPLE, GREY = "#2FBF71", "#E5484D", "#5B9CF6", "#A78BFA", "#64748B"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }}
.kw-head {{ display:flex; align-items:baseline; gap:14px; margin-bottom:4px; }}
.kw-title {{ font-size:26px; font-weight:600; color:{TEXT}; }}
.kw-sub {{ color:{MUTED}; font-size:13px; margin-bottom:18px; }}
.kw-card {{ background:{CARD}; border:1px solid {LINE}; border-radius:10px; padding:14px 16px 12px; margin-bottom:12px; }}
.kw-label {{ color:{MUTED}; font-size:11px; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:6px; }}
.kw-value {{ font-family:'IBM Plex Mono', monospace; font-size:22px; font-weight:600; color:{TEXT}; white-space:nowrap; }}
.kw-value.small {{ font-size:17px; }}
.kw-value.pos {{ color:{GREEN}; }}  .kw-value.neg {{ color:{RED}; }}
.kw-section {{ font-size:15px; font-weight:600; color:{TEXT}; margin:26px 0 10px; }}
.kw-acct {{ background:{CARD}; border:1px solid {LINE}; border-radius:10px; padding:16px 18px; margin-bottom:12px; }}
.kw-acct .name {{ font-size:15px; font-weight:600; color:{TEXT}; }}
.kw-acct .tag {{ font-family:'IBM Plex Mono', monospace; font-size:11px; color:{ACCENT}; margin-left:8px; }}
.kw-acct .row {{ display:flex; gap:28px; margin-top:12px; flex-wrap:wrap; }}
.kw-acct .k {{ color:{MUTED}; font-size:11px; letter-spacing:0.06em; text-transform:uppercase; }}
.kw-acct .v {{ font-family:'IBM Plex Mono', monospace; font-size:18px; font-weight:600; color:{TEXT}; margin-top:2px; }}
.kw-acct .v.pos {{ color:{GREEN}; }} .kw-acct .v.neg {{ color:{RED}; }}
.kw-bar {{ height:6px; background:{LINE}; border-radius:3px; margin-top:8px; overflow:hidden; }}
.kw-bar > div {{ height:100%; background:{PURPLE}; }}
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
        st.markdown("<div class='kw-head'><span class='kw-title'>Kona Wolf Trading</span></div>"
                    "<div class='kw-sub'>Sign in to view the accounts</div>", unsafe_allow_html=True)
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

TOKEN = st.session_state.session.access_token
sb.postgrest.auth(TOKEN)


# ---------------------------------------------------------------- data
@st.cache_data(ttl=120)
def load(token):
    sb.postgrest.auth(token)
    acct = pd.DataFrame(sb.table("accounts").select("*").execute().data)
    settings = pd.DataFrame(sb.table("account_settings").select("*").execute().data)
    expenses = pd.DataFrame(sb.table("expenses").select("*").order("spent_on", desc=True).execute().data)
    rows, start = [], 0
    while True:
        page = sb.table("deals").select("*").order("time").range(start, start + 999).execute().data
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    deals = pd.DataFrame(rows)
    snaps = pd.DataFrame(sb.table("snapshots").select("*").order("time", desc=True).limit(300).execute().data)
    pos = pd.DataFrame(sb.table("positions").select("*").execute().data)
    return acct, settings, expenses, deals, snaps, pos


acct, settings, expenses, deals, snaps, pos = load(TOKEN)
if deals.empty:
    st.warning("No trades yet. Check that the collector is running on the VPS.")
    st.stop()


def week_of(d):
    """Monday of the trading week. Sunday-evening trades belong to the coming week."""
    wd = d.weekday()
    return d + timedelta(days=7 - wd) if wd == 6 else d - timedelta(days=wd)


deals["time"] = pd.to_datetime(deals["time"], utc=True).dt.tz_convert(DAY_TZ)
deals["net"] = deals["profit"].fillna(0) + deals["commission"].fillna(0) + deals["swap"].fillna(0)
deals["date"] = deals["time"].dt.date
deals["week"] = deals["date"].map(week_of)
trades = deals[deals["entry"].isin([1, 3]) & deals["type"].isin([0, 1])].copy()
cash = deals[deals["type"] == 2].copy()
withdrawals = cash[cash["net"] < 0]

snaps = snaps.drop_duplicates("login") if not snaps.empty else snaps
latest = {r["login"]: r for _, r in snaps.iterrows()}

# account settings, with defaults for any account not yet configured
cfg = {}
for login in acct["login"]:
    row = settings[settings["login"] == login].iloc[0].to_dict() if not settings.empty and (settings["login"] == login).any() else {}
    cfg[login] = {
        "nickname": row.get("nickname") or str(login),
        "seed": float(row.get("seed_amount") or 0),
        "seed_repaid": float(row.get("seed_repaid") or 0),
        "seed_holder": row.get("seed_holder") or "Seed",
        "is_master": bool(row.get("is_master", False)),
        "pays_expenses": bool(row.get("pays_expenses", False)),
    }
logins = sorted(cfg, key=lambda l: (not cfg[l]["is_master"], cfg[l]["nickname"]))
master = next((l for l in logins if cfg[l]["is_master"]), logins[0])

# expenses: recurring spread evenly per week; one-offs charged in their week
if not expenses.empty:
    expenses["spent_on"] = pd.to_datetime(expenses["spent_on"]).dt.date
    expenses["amount"] = expenses["amount"].astype(float)
    monthly = expenses.loc[expenses["recurring"] == "monthly", "amount"].sum()
    yearly = expenses.loc[expenses["recurring"] == "yearly", "amount"].sum()
    oneoff = expenses[expenses["recurring"].isna()].copy()
    oneoff["week"] = oneoff["spent_on"].map(week_of)
else:
    monthly = yearly = 0.0
    oneoff = pd.DataFrame(columns=["week", "amount"])
WEEKLY_RECURRING = (monthly * 12 + yearly) / 52

today = datetime.now(pd.Timestamp.now(DAY_TZ).tz).date()
this_week = week_of(today)


# ---------------------------------------------------------------- payout engine
def compute_payouts(login):
    c = cfg[login]
    t = trades[trades["login"] == login]
    weekly = t.groupby("week")["net"].sum().sort_index()
    seed_left = max(c["seed"] - c["seed_repaid"], 0.0)
    carry = 0.0
    out = []
    for wk, gross in weekly.items():
        exp = 0.0
        if c["pays_expenses"]:
            exp = WEEKLY_RECURRING + oneoff.loc[oneoff["week"] == wk, "amount"].sum()
        base = gross - exp + carry
        if base <= 0:
            carry, seed_pay, ben, jesse = base, 0.0, 0.0, 0.0
        else:
            carry = 0.0
            seed_pay = min(base * 0.5, seed_left)
            seed_left -= seed_pay
            rest = base - seed_pay
            ben = jesse = rest / 2
        fri = wk + timedelta(days=4)
        w = withdrawals[(withdrawals["login"] == login) & (withdrawals["date"] >= fri) & (withdrawals["date"] < fri + timedelta(days=8))]
        out.append({"week": wk, "login": login, "account": c["nickname"], "gross": gross, "expenses": exp,
                    "seed": seed_pay, "ben": ben, "jesse": jesse, "ben_total": ben + exp,
                    "withdrawn": -w["net"].sum(), "in_progress": wk == this_week, "seed_left_after": seed_left})
    return pd.DataFrame(out), seed_left


payouts, seed_left = {}, {}
for l in logins:
    payouts[l], seed_left[l] = compute_payouts(l)
allp = pd.concat(payouts.values(), ignore_index=True) if payouts else pd.DataFrame()
cur = allp[allp["week"] == this_week] if not allp.empty else pd.DataFrame()


# ---------------------------------------------------------------- helpers
def money(v):
    return f"{v:,.2f}"


def card(col, label, value, signed=None, small=False):
    cls = "small" if small else ""
    if signed is not None:
        cls += " pos" if signed > 0 else (" neg" if signed < 0 else "")
    col.markdown(f"<div class='kw-card'><div class='kw-label'>{label}</div><div class='kw-value {cls}'>{value}</div></div>",
                 unsafe_allow_html=True)


def section(title):
    st.markdown(f"<div class='kw-section'>{title}</div>", unsafe_allow_html=True)


def chart_layout(fig, height, legend=False):
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor=CARD, plot_bgcolor=CARD,
                      font=dict(family="IBM Plex Sans", color=MUTED, size=12), barmode="relative",
                      xaxis=dict(gridcolor=LINE, zerolinecolor=LINE), yaxis=dict(gridcolor=LINE, zerolinecolor=LINE),
                      showlegend=legend, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11), orientation="h", y=1.08))
    return fig


def sgn(v):
    return "pos" if v > 0 else ("neg" if v < 0 else "")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<div class='kw-label'>Signed in</div><div style='font-size:13px;color:{TEXT}'>{st.session_state.session.user.email}</div>",
                unsafe_allow_html=True)
    sync_times = [pd.to_datetime(r["time"]) for r in latest.values()]
    last_sync = max(sync_times).tz_convert("America/New_York").strftime("%b %d, %I:%M %p") if sync_times else "—"
    st.markdown(f"<div class='kw-label' style='margin-top:14px'>Last sync</div><div style='font-size:13px;color:{TEXT}'>{last_sync} ET</div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='kw-label' style='margin-top:14px'>Weekly expenses</div><div style='font-size:13px;color:{TEXT}'>${WEEKLY_RECURRING:,.2f} recurring</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        del st.session_state.session
        st.rerun()

# ---------------------------------------------------------------- header: this week, all accounts
st.markdown(f"<div class='kw-head'><span class='kw-title'>Kona Wolf Trading</span></div>"
            f"<div class='kw-sub'>Week of {this_week:%b %d} · {len(logins)} account{'s' if len(logins) != 1 else ''} · payout Friday {this_week + timedelta(days=4):%b %d}</div>",
            unsafe_allow_html=True)

g = cur["gross"].sum() if not cur.empty else 0
e = cur["expenses"].sum() if not cur.empty else 0
sd = cur["seed"].sum() if not cur.empty else 0
b = cur["ben"].sum() if not cur.empty else 0
j = cur["jesse"].sum() if not cur.empty else 0
c = st.columns(5)
card(c[0], "Gross this week", money(g), g)
card(c[1], "Expenses → Ben", money(e))
card(c[2], "Seed → Donna", money(sd))
card(c[3], "Ben", money(b), b)
card(c[4], "Jesse", money(j), j)

# ---------------------------------------------------------------- per-account
section("Accounts")
master_week = payouts[master].loc[payouts[master]["week"] == this_week, "gross"].sum() if not payouts[master].empty else 0
for l in logins:
    c_ = cfg[l]
    snap = latest.get(l, {})
    bal = float(snap.get("balance", 0) or 0)
    above = bal - BASE
    p = payouts[l]
    wk = p[p["week"] == this_week]
    wk_gross = wk["gross"].sum() if not wk.empty else 0
    t = trades[trades["login"] == l]
    today_pl = t.loc[t["date"] == today, "net"].sum()
    seed_total = c_["seed"]
    repaid = seed_total - seed_left[l]
    parts = [
        ("Balance", money(bal), ""),
        ("Above 50k", f"{above:+,.2f}", sgn(above)),
        ("This week", f"{wk_gross:+,.2f}", sgn(wk_gross)),
        ("Today", f"{today_pl:+,.2f}", sgn(today_pl)),
    ]
    if not c_["is_master"]:
        drift = wk_gross - master_week
        parts.append(("vs main this week", f"{drift:+,.2f}", sgn(drift)))
    if seed_total > 0 and seed_left[l] > 0:
        parts.append((f"Owed to {c_['seed_holder']}", money(seed_left[l]), ""))
    html = "".join(f"<div><div class='k'>{k}</div><div class='v {cls}'>{v}</div></div>" for k, v, cls in parts)
    tag = "MASTER" if c_["is_master"] else "COPY"
    bar = ""
    if seed_total > 0 and seed_left[l] > 0:
        pct = repaid / seed_total * 100
        bar = f"<div class='k' style='margin-top:12px'>Seed repaid {pct:.0f}%</div><div class='kw-bar'><div style='width:{pct:.1f}%'></div></div>"
    st.markdown(f"<div class='kw-acct'><span class='name'>{c_['nickname']}</span><span class='tag'>#{l} · {tag}</span>"
                f"<div class='row'>{html}</div>{bar}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- weekly payouts chart
section("Weekly payouts (all accounts)")
if not allp.empty:
    wk_sum = allp.groupby("week")[["jesse", "ben", "seed", "expenses"]].sum().sort_index().tail(16)
    x = [f"{w:%b %d}" for w in wk_sum.index]
    fig = go.Figure()
    for col, name, color in [("jesse", "Jesse", BLUE), ("ben", "Ben", GREEN), ("seed", "Seed → Donna", PURPLE), ("expenses", "Expenses", GREY)]:
        fig.add_bar(x=x, y=wk_sum[col], name=name, marker_color=color, hovertemplate="%{x}<br>" + name + " %{y:,.0f}<extra></extra>")
    st.plotly_chart(chart_layout(fig, 320, legend=True), use_container_width=True)

# ---------------------------------------------------------------- payout history
section("Payout history")
if not allp.empty:
    hist = allp.sort_values(["week", "account"], ascending=[False, True]).head(60).copy()
    hist["Week"] = hist["week"].map(lambda w: f"{w:%b %d}") + hist["in_progress"].map(lambda x: " (in progress)" if x else "")
    show = hist[["Week", "account", "gross", "expenses", "seed", "ben", "jesse", "ben_total", "withdrawn"]].rename(columns={
        "account": "Account", "gross": "Gross", "expenses": "Expenses", "seed": "Seed → Donna",
        "ben": "Ben", "jesse": "Jesse", "ben_total": "Ben incl. expenses", "withdrawn": "Withdrawn (MT5)"})
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={k: st.column_config.NumberColumn(format="$%.2f") for k in show.columns if k not in ("Week", "Account")})

# ---------------------------------------------------------------- seed tracker
seeded = [l for l in logins if cfg[l]["seed"] > 0 and seed_left[l] > 0]
if seeded:
    section("Seed repayment")
    cols = st.columns(len(seeded))
    for col, l in zip(cols, seeded):
        c_ = cfg[l]
        p = payouts[l]
        recent = p[~p["in_progress"]].tail(4)["seed"]
        rate = recent.mean() if len(recent) else 0
        weeks_left = seed_left[l] / rate if rate > 0 else None
        eta = (this_week + timedelta(weeks=round(weeks_left))).strftime("%b %d, %Y") if weeks_left else "—"
        col.markdown(f"<div class='kw-card'><div class='kw-label'>{c_['nickname']} · owed to {c_['seed_holder']}</div>"
                     f"<div class='kw-value'>{money(seed_left[l])}</div>"
                     f"<div style='color:{MUTED};font-size:12px;margin-top:6px'>of {money(c_['seed'])} · avg {money(rate)}/wk · paid off ≈ {eta}</div></div>",
                     unsafe_allow_html=True)

# ---------------------------------------------------------------- expenses
section("Expenses")
ex_left, ex_right = st.columns([1, 1.6])
with ex_left:
    with st.form("add_expense", clear_on_submit=True):
        d = st.date_input("Date", value=today)
        desc = st.text_input("Description")
        amt = st.number_input("Amount ($)", min_value=0.0, step=1.0, format="%.2f")
        rec = st.selectbox("Repeats", ["One-off", "Monthly", "Yearly"])
        if st.form_submit_button("Add expense", use_container_width=True):
            if desc and amt > 0:
                sb.table("expenses").insert({"spent_on": d.isoformat(), "description": desc, "amount": amt,
                                             "recurring": None if rec == "One-off" else rec.lower()}).execute()
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Enter a description and an amount.")
with ex_right:
    if expenses.empty:
        st.caption("No expenses recorded.")
    else:
        ex = expenses.copy()
        ex["recurring"] = ex["recurring"].fillna("one-off")
        st.dataframe(ex[["spent_on", "description", "amount", "recurring"]].rename(columns={"spent_on": "Date", "description": "Item", "amount": "Amount", "recurring": "Repeats"}),
                     use_container_width=True, hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="$%.2f")})
        del_id = st.selectbox("Remove an expense", ["—"] + [f"{r['id']} · {r['description']} ${r['amount']:.2f}" for _, r in expenses.iterrows()])
        if del_id != "—" and st.button("Remove"):
            sb.table("expenses").delete().eq("id", int(del_id.split(" ·")[0])).execute()
            st.cache_data.clear()
            st.rerun()

# ---------------------------------------------------------------- account selector for calendar / stats / trades
section("Calendar")
sel_cols = st.columns([1.4, 1, 1, 3, 1.4])
names = ["All accounts"] + [cfg[l]["nickname"] for l in logins]
sel = sel_cols[0].selectbox("Account", names, label_visibility="collapsed")
sel_login = None if sel == "All accounts" else logins[names.index(sel) - 1]
tsel = trades if sel_login is None else trades[trades["login"] == sel_login]
daily = tsel.groupby("date")["net"].sum()

months = sorted({(d.year, d.month) for d in trades["date"]})
if "cal_idx" not in st.session_state:
    st.session_state.cal_idx = len(months) - 1
if sel_cols[1].button("◀ Prev", use_container_width=True, disabled=st.session_state.cal_idx == 0):
    st.session_state.cal_idx -= 1
    st.rerun()
if sel_cols[2].button("Next ▶", use_container_width=True, disabled=st.session_state.cal_idx == len(months) - 1):
    st.session_state.cal_idx += 1
    st.rerun()
pick = sel_cols[4].selectbox("Month", months, index=st.session_state.cal_idx, label_visibility="collapsed",
                             format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}")
if months.index(pick) != st.session_state.cal_idx:
    st.session_state.cal_idx = months.index(pick)
    st.rerun()
year, month = months[st.session_state.cal_idx]

month_daily = daily[[d.year == year and d.month == month for d in daily.index]]
m_total = month_daily.sum()
base_for_pct = BASE * (len(logins) if sel_login is None else 1)
col = GREEN if m_total >= 0 else RED
st.markdown(f"<div class='kw-monthline'><span style='color:{TEXT};font-size:18px'>{calendar.month_name[month]} {year}</span>"
            f"&nbsp;&nbsp;&nbsp;<span style='color:{col}'>{m_total:+,.2f}</span>"
            f"&nbsp;<span style='color:{col};opacity:0.7'>({m_total / base_for_pct * 100:+.2f}% of base)</span></div>", unsafe_allow_html=True)

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
            cols[i].markdown(f"<div class='kw-day {cls}'><div class='n'>{day}</div><div class='v'>{val:+,.0f}</div>"
                             f"<div class='p'>{val / base_for_pct * 100:+.2f}%</div></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- risk stats
section(f"Risk · {sel}")
wins = tsel[tsel["net"] > 0]
losses = tsel[tsel["net"] < 0]
n = len(tsel)
aw = wins["net"].mean() if len(wins) else 0
al = losses["net"].mean() if len(losses) else 0
pf = wins["net"].sum() / abs(losses["net"].sum()) if len(losses) and losses["net"].sum() != 0 else 0
weekly_sel = tsel.groupby("week")["net"].sum()
# worst drawdown below base inside any week (running sum within the week)
dd = 0.0
for wk, grp in tsel.sort_values("time").groupby("week"):
    run = grp["net"].cumsum()
    dd = min(dd, run.min())
streak = 0
for v in daily.sort_index(ascending=False):
    if v < 0:
        streak += 1
    else:
        break
c = st.columns(4)
card(c[0], "Win rate", f"{len(wins) / n * 100 if n else 0:.0f}%")
card(c[1], "Profit factor", f"{pf:.2f}")
card(c[2], "Avg win / loss", f"{aw:,.0f} / {al:,.0f}", small=True)
card(c[3], "Trades", f"{n:,}")
c = st.columns(4)
card(c[0], "Worst day", money(daily.min() if len(daily) else 0), -1)
card(c[1], "Worst week", money(weekly_sel.min() if len(weekly_sel) else 0), -1)
card(c[2], "Deepest dip below 50k", money(dd), -1 if dd < 0 else None)
card(c[3], "Losing days in a row", f"{streak}", -1 if streak else None)

# ---------------------------------------------------------------- trades
section(f"Trades · {sel}")
tab_open, tab_closed = st.tabs(["Open", "Closed"])
with tab_open:
    p_ = pos if sel_login is None else pos[pos["login"] == sel_login] if not pos.empty else pos
    if p_.empty:
        st.caption("No open positions.")
    else:
        p_ = p_.copy()
        p_["type"] = p_["type"].map({0: "Buy", 1: "Sell"})
        p_["account"] = p_["login"].map(lambda l: cfg.get(l, {}).get("nickname", l))
        st.dataframe(p_[["account", "ticket", "time", "type", "symbol", "volume", "price_open", "price_current", "sl", "tp", "profit"]],
                     use_container_width=True, hide_index=True)
with tab_closed:
    show = tsel.sort_values("time", ascending=False).copy()
    show["account"] = show["login"].map(lambda l: cfg[l]["nickname"])
    show["time"] = show["time"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(show[["account", "ticket", "time", "symbol", "volume", "price", "commission", "swap", "profit", "net"]].head(500),
                 use_container_width=True, hide_index=True)
