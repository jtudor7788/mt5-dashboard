import calendar
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Kona Wolf Trading", page_icon="📈", layout="wide")

DAY_TZ = "America/New_York"   # clock that decides which day/week a trade belongs to
STALE_MINUTES = 20            # warn if the VPS hasn't synced in this long
MATCH_TOLERANCE = 5.00        # $ difference allowed between expected and actual withdrawal

# ---------------------------------------------------------------- palette
CARD, LINE = "#121A2B", "#1E2A40"
TEXT, MUTED, ACCENT = "#E6EBF5", "#8A94A8", "#F0B429"
GREEN, RED, BLUE, PURPLE, GREY = "#2FBF71", "#E5484D", "#5B9CF6", "#A78BFA", "#64748B"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }}
.kw-head {{ display:flex; align-items:baseline; gap:14px; margin-bottom:4px; flex-wrap:wrap; }}
.kw-title {{ font-size:24px; font-weight:600; color:{TEXT}; }}
.kw-sub {{ color:{MUTED}; font-size:13px; margin-bottom:16px; }}
.kw-note {{ color:{MUTED}; font-size:12px; margin:0 0 6px; line-height:1.5; }}
.kw-section {{ font-size:15px; font-weight:600; color:{TEXT}; margin:24px 0 10px; }}
.kw-alert {{ background:#3A1B1F; border:1px solid #6A2A2A; color:#F5B5B8; border-radius:10px; padding:10px 14px; font-size:13px; margin-bottom:12px; }}
.kw-grid {{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px; margin-bottom:10px; }}
.kw-card {{ background:{CARD}; border:1px solid {LINE}; border-radius:10px; padding:12px 14px 10px; min-width:0; }}
.kw-label {{ color:{MUTED}; font-size:10.5px; letter-spacing:0.07em; text-transform:uppercase; margin-bottom:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kw-value {{ font-family:'IBM Plex Mono', monospace; font-size:20px; font-weight:600; color:{TEXT}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kw-value.small {{ font-size:16px; }}
.kw-value.pos {{ color:{GREEN}; }}  .kw-value.neg {{ color:{RED}; }}
.kw-acct {{ background:{CARD}; border:1px solid {LINE}; border-radius:10px; padding:14px 16px; margin-bottom:10px; }}
.kw-acct .name {{ font-size:15px; font-weight:600; color:{TEXT}; }}
.kw-acct .tag {{ font-family:'IBM Plex Mono', monospace; font-size:11px; color:{ACCENT}; margin-left:8px; }}
.kw-acct .row {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:10px 18px; margin-top:10px; }}
.kw-acct .k {{ color:{MUTED}; font-size:10.5px; letter-spacing:0.06em; text-transform:uppercase; }}
.kw-acct .v {{ font-family:'IBM Plex Mono', monospace; font-size:17px; font-weight:600; color:{TEXT}; margin-top:2px; white-space:nowrap; }}
.kw-acct .v.pos {{ color:{GREEN}; }} .kw-acct .v.neg {{ color:{RED}; }}
.kw-bar {{ height:6px; background:{LINE}; border-radius:3px; margin-top:8px; overflow:hidden; }}
.kw-bar > div {{ height:100%; background:{PURPLE}; }}
.kw-cal {{ display:grid; grid-template-columns:repeat(7, minmax(0,1fr)); gap:6px; }}
.kw-dow {{ text-align:center; color:{MUTED}; font-size:10.5px; letter-spacing:0.07em; text-transform:uppercase; padding-bottom:4px; }}
.kw-day {{ border-radius:8px; padding:8px 4px; min-height:78px; text-align:center; font-family:'IBM Plex Mono', monospace; border:1px solid {LINE}; min-width:0; }}
.kw-day .n {{ font-size:11px; color:{MUTED}; }}
.kw-day .v {{ font-size:14px; font-weight:600; margin-top:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kw-day .p {{ font-size:10.5px; opacity:0.8; white-space:nowrap; }}
.kw-day.pos {{ background:#12352A; border-color:#1F5A45; color:{GREEN}; }}
.kw-day.neg {{ background:#3A1B1F; border-color:#6A2A2A; color:{RED}; }}
.kw-day.flat {{ background:{CARD}; color:{TEXT}; }}
.kw-day.empty {{ background:transparent; border-color:transparent; }}
.kw-monthline {{ font-family:'IBM Plex Mono', monospace; font-size:15px; margin:6px 0 10px; }}
div[data-testid="stSidebar"] {{ background:{CARD}; border-right:1px solid {LINE}; }}
@media (max-width: 700px) {{
  .block-container {{ padding-left:0.8rem; padding-right:0.8rem; padding-top:1rem; }}
  .kw-title {{ font-size:20px; }}
  .kw-grid {{ grid-template-columns:repeat(2, minmax(0,1fr)); gap:8px; }}
  .kw-card {{ padding:10px 12px 8px; }}
  .kw-value {{ font-size:17px; }}  .kw-value.small {{ font-size:14px; }}
  .kw-acct .row {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
  .kw-acct .v {{ font-size:15px; }}
  .kw-cal {{ gap:3px; }}
  .kw-day {{ min-height:58px; padding:5px 2px; border-radius:6px; }}
  .kw-day .n {{ font-size:9.5px; }}
  .kw-day .v {{ font-size:10.5px; margin-top:3px; }}
  .kw-day .p {{ display:none; }}
  .kw-dow {{ font-size:9px; }}
  div[data-testid="stHorizontalBlock"] {{ flex-wrap:nowrap !important; gap:6px !important; }}
  div[data-testid="stHorizontalBlock"] > div {{ min-width:0 !important; flex:1 1 0 !important; }}
}}
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
    ledger = pd.DataFrame(sb.table("payouts").select("*").execute().data)
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
    return acct, settings, expenses, ledger, deals, snaps, pos


acct, settings, expenses, ledger, deals, snaps, pos = load(TOKEN)
if deals.empty:
    st.warning("No trades yet. Check that the collector is running on the VPS.")
    st.stop()


def week_of(d):
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

today = datetime.now(pd.Timestamp.now(DAY_TZ).tz).date()
this_week = week_of(today)
now_utc = pd.Timestamp.now(tz="UTC")

cfg = {}
for login in acct["login"]:
    row = settings[settings["login"] == login].iloc[0].to_dict() if not settings.empty and (settings["login"] == login).any() else {}
    so = row.get("started_on")
    cfg[login] = {
        "nickname": row.get("nickname") or str(login),
        "seed": float(row.get("seed_amount") or 0),
        "seed_repaid": float(row.get("seed_repaid") or 0),
        "seed_holder": row.get("seed_holder") or "Seed",
        "is_master": bool(row.get("is_master", False)),
        "pays_expenses": bool(row.get("pays_expenses", False)),
        "base": float(row.get("base_amount") or 50000),
        "started_on": pd.to_datetime(so).date() if so else date(2000, 1, 1),
        "prior_ben": float(row.get("prior_ben") or 0),
        "prior_jesse": float(row.get("prior_jesse") or 0),
        "prior_seed": float(row.get("prior_seed") or 0),
    }
logins = sorted(cfg, key=lambda l: (not cfg[l]["is_master"], cfg[l]["nickname"]))
master = next((l for l in logins if cfg[l]["is_master"]), logins[0])

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

if not ledger.empty:
    ledger["week"] = pd.to_datetime(ledger["week"]).dt.date
    for c in ["gross", "expenses", "seed", "ben", "jesse"]:
        ledger[c] = ledger[c].astype(float)
frozen = {(r["week"], r["login"]): r for _, r in ledger.iterrows()} if not ledger.empty else {}


# ---------------------------------------------------------------- payout engine
def compute_payouts(login):
    c = cfg[login]
    t = trades[trades["login"] == login]
    weekly = t.groupby("week")["net"].sum().sort_index()
    seed_left = max(c["seed"] - c["seed_repaid"], 0.0)
    carry = 0.0
    out = []
    for wk, gross in weekly.items():
        fri = wk + timedelta(days=4)
        w = withdrawals[(withdrawals["login"] == login) & (withdrawals["date"] >= fri) & (withdrawals["date"] < fri + timedelta(days=8))]
        withdrawn = -w["net"].sum()
        tracked = wk >= c["started_on"]
        key = (wk, login)
        if key in frozen:
            f = frozen[key]
            exp, seed_pay, ben, jesse = f["expenses"], f["seed"], f["ben"], f["jesse"]
            gross = f["gross"]
            seed_left = max(seed_left - seed_pay, 0.0)
            carry = 0.0
            status = "paid"
        elif not tracked:
            exp = seed_pay = ben = jesse = 0.0
            status = "before tracking"
        else:
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
            if wk == this_week:
                status = "in progress"
            elif withdrawn == 0 and today < fri + timedelta(days=8):
                status = "pending"
            elif abs(withdrawn - (ben + jesse + exp + seed_pay)) > MATCH_TOLERANCE:
                status = "⚠ mismatch"
            else:
                status = "✓ matched"
        if status == "paid":
            expected = ben + jesse + exp + seed_pay
            if withdrawn == 0 and today < fri + timedelta(days=8):
                status = "paid · pending"
            elif abs(withdrawn - expected) > MATCH_TOLERANCE:
                status = "paid · ⚠ mismatch"
            else:
                status = "paid ✓"
        out.append({"week": wk, "login": login, "account": c["nickname"], "gross": gross, "expenses": exp,
                    "seed": seed_pay, "ben": ben, "jesse": jesse, "ben_total": ben + exp,
                    "expected_withdrawal": ben + jesse + exp + seed_pay, "withdrawn": withdrawn,
                    "status": status, "tracked": tracked, "in_progress": wk == this_week, "frozen": key in frozen})
    return pd.DataFrame(out), seed_left


payouts, seed_left = {}, {}
for l in logins:
    payouts[l], seed_left[l] = compute_payouts(l)
allp = pd.concat(payouts.values(), ignore_index=True) if payouts else pd.DataFrame()
cur = allp[allp["week"] == this_week] if not allp.empty else pd.DataFrame()
tracked = allp[allp["tracked"]] if not allp.empty else pd.DataFrame()


# ---------------------------------------------------------------- helpers
def money(v):
    return f"{v:,.2f}"


def sgn(v):
    return "pos" if v > 0 else ("neg" if v < 0 else "")


def cards(items):
    html = "".join(f"<div class='kw-card'><div class='kw-label'>{l}</div><div class='kw-value {c}'>{v}</div></div>" for l, v, c in items)
    st.markdown(f"<div class='kw-grid'>{html}</div>", unsafe_allow_html=True)


def section(title):
    st.markdown(f"<div class='kw-section'>{title}</div>", unsafe_allow_html=True)


def chart_layout(fig, height, legend=False):
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor=CARD, plot_bgcolor=CARD,
                      font=dict(family="IBM Plex Sans", color=MUTED, size=12), barmode="relative",
                      xaxis=dict(gridcolor=LINE, zerolinecolor=LINE), yaxis=dict(gridcolor=LINE, zerolinecolor=LINE),
                      showlegend=legend, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11), orientation="h", y=1.08))
    return fig


def summary_text(wk):
    rows = allp[(allp["week"] == wk)]
    lines = [f"Kona Wolf Trading — week of {wk:%b %d, %Y} (payout Fri {wk + timedelta(days=4):%b %d})", ""]
    for _, r in rows.iterrows():
        lines.append(f"{r['account']} (#{r['login']})")
        lines.append(f"  Gross profit:        ${r['gross']:,.2f}")
        if r["seed"]:
            lines.append(f"  Seed → {cfg[r['login']]['seed_holder']}:        ${r['seed']:,.2f}")
        lines.append(f"  Profit split each:   ${r['ben'] + r['expenses'] / 2:,.2f}")
        if r["expenses"]:
            lines.append(f"  Expenses (Ben card): ${r['expenses']:,.2f}  -> Jesse pays Ben half: ${r['expenses'] / 2:,.2f}")
        lines.append(f"  Ben receives:        ${r['ben'] + r['expenses']:,.2f}")
        lines.append(f"  Jesse receives:      ${r['jesse']:,.2f}")
        lines.append(f"  Withdraw total:    ${r['expected_withdrawal']:,.2f}")
        lines.append("")
    if len(rows) > 1:
        lines.append(f"ALL ACCOUNTS — Ben ${(rows['ben'] + rows['expenses']).sum():,.2f} · Jesse ${rows['jesse'].sum():,.2f} · Seed ${rows['seed'].sum():,.2f} · Withdraw ${rows['expected_withdrawal'].sum():,.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<div class='kw-label'>Signed in</div><div style='font-size:13px;color:{TEXT}'>{st.session_state.session.user.email}</div>",
                unsafe_allow_html=True)
    sync_times = [pd.to_datetime(r["time"]) for r in latest.values()]
    last_sync_ts = max(sync_times) if sync_times else None
    last_sync = last_sync_ts.tz_convert("America/New_York").strftime("%b %d, %I:%M %p") if last_sync_ts is not None else "—"
    st.markdown(f"<div class='kw-label' style='margin-top:14px'>Last sync</div><div style='font-size:13px;color:{TEXT}'>{last_sync} ET</div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='kw-label' style='margin-top:14px'>Weekly expenses</div><div style='font-size:13px;color:{TEXT}'>${WEEKLY_RECURRING:,.2f} recurring</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if not tracked.empty:
        st.download_button("Download payouts (CSV)", tracked.drop(columns=["in_progress", "frozen", "tracked"]).to_csv(index=False).encode(),
                           "payouts.csv", "text/csv", use_container_width=True)
    tcsv = trades.copy()
    tcsv["time"] = tcsv["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.download_button("Download trades (CSV)", tcsv.drop(columns=["date", "week"]).to_csv(index=False).encode(),
                       "trades.csv", "text/csv", use_container_width=True)
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        del st.session_state.session
        st.rerun()

# ---------------------------------------------------------------- stale-data banner
if last_sync_ts is not None:
    age = (now_utc - last_sync_ts).total_seconds() / 60
    if age > STALE_MINUTES:
        st.markdown(f"<div class='kw-alert'>⚠ Data is {age:.0f} minutes old. The VPS collector hasn't synced since {last_sync} ET — check that MT5 is logged in and the scheduled task is running.</div>",
                    unsafe_allow_html=True)

# ---------------------------------------------------------------- header: this week, all accounts
st.markdown(f"<div class='kw-head'><span class='kw-title'>Kona Wolf Trading</span></div>"
            f"<div class='kw-sub'>Week of {this_week:%b %d} · {len(logins)} account{'s' if len(logins) != 1 else ''} · payout Friday {this_week + timedelta(days=4):%b %d}</div>",
            unsafe_allow_html=True)

g = cur["gross"].sum() if not cur.empty else 0
e = cur["expenses"].sum() if not cur.empty else 0
sd = cur["seed"].sum() if not cur.empty else 0
b = cur["ben"].sum() if not cur.empty else 0
j = cur["jesse"].sum() if not cur.empty else 0
half = e / 2
share = b + half          # each partner's 50% of profit after seed, before expenses
cards([("Gross this week", money(g), sgn(g)), ("Seed → Donna", money(sd), ""),
       ("Expenses on Ben's card", money(e), ""), ("Jesse → Ben for half", money(half), "")])
cards([("Ben · profit split", money(share), sgn(share)), ("Ben receives", money(b + e), sgn(b + e)),
       ("Jesse · profit split", money(share), sgn(share)), ("Jesse receives", money(j), sgn(j))])
st.markdown(f"<div class='kw-note'>Profit splits 50/50 at {money(share)} each. Expenses of {money(e)} were paid on Ben's card, so Jesse's half ({money(half)}) "
            f"moves from Jesse's share to Ben. Ben receives {money(share)} + {money(half)} = {money(b + e)}. Jesse receives {money(share)} − {money(half)} = {money(j)}.</div>",
            unsafe_allow_html=True)

# ---------------------------------------------------------------- running totals
prior_ben = sum(cfg[l]["prior_ben"] for l in logins)
prior_jesse = sum(cfg[l]["prior_jesse"] for l in logins)
prior_seed = sum(cfg[l]["prior_seed"] for l in logins)
if not tracked.empty or prior_ben or prior_jesse or prior_seed:
    section("Totals to date")
    tb = (tracked["ben"] + tracked["expenses"]).sum() if not tracked.empty else 0
    tj = tracked["jesse"].sum() if not tracked.empty else 0
    ts = tracked["seed"].sum() if not tracked.empty else 0
    te = tracked["expenses"].sum() if not tracked.empty else 0
    tg = tracked["gross"].sum() if not tracked.empty else 0
    cards([("Ben · all time", money(prior_ben + tb), "pos"),
           ("Jesse · all time", money(prior_jesse + tj), "pos"),
           ("Donna · seed repaid", money(prior_seed + ts), ""),
           ("Expenses on Ben's card · since ledger", money(te), "")])
    cards([("Ben · since ledger", money(tb), "pos"),
           ("Jesse · since ledger", money(tj), "pos"),
           ("Donna · since ledger", money(ts), ""),
           ("Gross · since ledger", money(tg), sgn(tg))])
    st.markdown(f"<div class='kw-note'>All-time figures include payouts made before the ledger started (Ben {money(prior_ben)}, Jesse {money(prior_jesse)}, Donna {money(prior_seed)}).</div>",
                unsafe_allow_html=True)

# ---------------------------------------------------------------- per-account
section("Accounts")
mp = payouts[master]
master_week = mp.loc[mp["week"] == this_week, "gross"].sum() if not mp.empty else 0
for l in logins:
    c_ = cfg[l]
    snap = latest.get(l, {})
    bal = float(snap.get("balance", 0) or 0)
    above = bal - c_["base"]
    p = payouts[l]
    wk = p[p["week"] == this_week]
    wk_gross = wk["gross"].sum() if not wk.empty else 0
    t = trades[trades["login"] == l]
    today_pl = t.loc[t["date"] == today, "net"].sum()
    seed_total = c_["seed"]
    repaid = seed_total - seed_left[l]
    parts = [("Balance", money(bal), ""), (f"Above {c_['base'] / 1000:.0f}k", f"{above:+,.2f}", sgn(above)),
             ("This week", f"{wk_gross:+,.2f}", sgn(wk_gross)), ("Today", f"{today_pl:+,.2f}", sgn(today_pl))]
    ml = float(snap.get("margin_level") or 0)
    if ml:
        parts.append(("Margin level", f"{ml:,.0f}%", "neg" if ml < 200 else ""))
    if not c_["is_master"]:
        drift = wk_gross - master_week
        parts.append(("vs main this week", f"{drift:+,.2f}", sgn(drift)))
        done = p[~p["in_progress"]].tail(8).set_index("week")["gross"]
        mdone = mp.set_index("week")["gross"].reindex(done.index).fillna(0)
        if len(done):
            avg_drift = (done - mdone).mean()
            parts.append(("Avg drift · last 8 wks", f"{avg_drift:+,.2f}", sgn(avg_drift)))
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

# ---------------------------------------------------------------- friday summary
section("Friday summary")
week_opts = sorted(tracked["week"].unique(), reverse=True) if not tracked.empty else [this_week]
wsel = st.selectbox("Week", week_opts, format_func=lambda w: f"Week of {w:%b %d}" + (" (in progress)" if w == this_week else ""), label_visibility="collapsed")
st.code(summary_text(wsel), language=None)
st.markdown("<div class='kw-note'>Tap the copy icon in the top-right of the box, then paste into a text to Ben or Donna.</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- weekly payouts chart
section("Weekly payouts (all accounts)")
if not tracked.empty:
    wk_sum = tracked.groupby("week")[["jesse", "ben", "seed", "expenses"]].sum().sort_index().tail(16)
    x = [f"{w:%b %d}" for w in wk_sum.index]
    fig = go.Figure()
    for col, name, color in [("jesse", "Jesse", BLUE), ("ben", "Ben", GREEN), ("seed", "Seed → Donna", PURPLE), ("expenses", "Expenses", GREY)]:
        fig.add_bar(x=x, y=wk_sum[col], name=name, marker_color=color, hovertemplate="%{x}<br>" + name + " %{y:,.0f}<extra></extra>")
    st.plotly_chart(chart_layout(fig, 300, legend=True), use_container_width=True, config={"displayModeBar": False})
else:
    st.caption("No tracked weeks yet — check started_on in account_settings.")

# ---------------------------------------------------------------- payout history + mark paid
section("Payout history")
if not allp.empty:
    hist = allp.sort_values(["week", "account"], ascending=[False, True]).head(80).copy()
    hist["Week"] = hist["week"].map(lambda w: f"{w:%b %d}")
    hist["split_each"] = hist["ben"] + hist["expenses"] / 2
    hist["jesse_to_ben"] = hist["expenses"] / 2
    show = hist[["Week", "account", "status", "gross", "seed", "expenses", "split_each", "jesse_to_ben", "ben_total", "jesse", "expected_withdrawal", "withdrawn"]].rename(columns={
        "account": "Account", "status": "Status", "gross": "Gross", "seed": "Seed → Donna", "expenses": "Expenses (Ben's card)",
        "split_each": "Profit split each", "jesse_to_ben": "Jesse → Ben", "ben_total": "Ben receives", "jesse": "Jesse receives",
        "expected_withdrawal": "Should withdraw", "withdrawn": "Withdrawn (MT5)"})
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={k: st.column_config.NumberColumn(format="$%.2f") for k in show.columns if k not in ("Week", "Account", "Status")})

    with st.expander("Mark a week as paid / undo"):
        st.markdown("<div class='kw-note'>Marking a week paid freezes its split so later changes to expenses or seed settings don't rewrite history. "
                    "The withdrawn column stays live from MT5 so a mismatch still shows.</div>", unsafe_allow_html=True)
        unpaid = tracked[(~tracked["frozen"]) & (~tracked["in_progress"])].sort_values("week", ascending=False)
        paid = tracked[tracked["frozen"]].sort_values("week", ascending=False)
        cA, cB = st.columns(2)
        with cA:
            if unpaid.empty:
                st.caption("Nothing waiting to be marked.")
            else:
                opts = {f"{r['week']:%b %d} · {r['account']} · Ben receives {money(r['ben'] + r['expenses'])} / Jesse receives {money(r['jesse'])}": (r["week"], r["login"]) for _, r in unpaid.iterrows()}
                ch = st.selectbox("Unpaid weeks", list(opts.keys()))
                note = st.text_input("Note (optional)")
                if st.button("Mark paid", use_container_width=True):
                    wk_, lg_ = opts[ch]
                    r = unpaid[(unpaid["week"] == wk_) & (unpaid["login"] == lg_)].iloc[0]
                    sb.table("payouts").upsert({"week": wk_.isoformat(), "login": int(lg_), "gross": float(r["gross"]), "expenses": float(r["expenses"]),
                                                "seed": float(r["seed"]), "ben": float(r["ben"]), "jesse": float(r["jesse"]),
                                                "paid_on": today.isoformat(), "note": note or None}).execute()
                    st.cache_data.clear()
                    st.rerun()
        with cB:
            if paid.empty:
                st.caption("No weeks marked paid yet.")
            else:
                opts2 = {f"{r['week']:%b %d} · {r['account']}": (r["week"], r["login"]) for _, r in paid.iterrows()}
                ch2 = st.selectbox("Paid weeks", list(opts2.keys()))
                if st.button("Undo mark", use_container_width=True):
                    wk_, lg_ = opts2[ch2]
                    sb.table("payouts").delete().eq("week", wk_.isoformat()).eq("login", int(lg_)).execute()
                    st.cache_data.clear()
                    st.rerun()

# ---------------------------------------------------------------- seed tracker
seeded = [l for l in logins if cfg[l]["seed"] > 0 and seed_left[l] > 0]
if seeded:
    section("Seed repayment")
    items = []
    for l in seeded:
        c_ = cfg[l]
        p = payouts[l]
        recent = p[(~p["in_progress"]) & p["tracked"]].tail(4)["seed"]
        rate = recent.mean() if len(recent) else 0
        weeks_left = seed_left[l] / rate if rate > 0 else None
        eta = (this_week + timedelta(weeks=round(weeks_left))).strftime("%b %d, %Y") if weeks_left else "—"
        items.append((f"{c_['nickname']} · owed to {c_['seed_holder']}", money(seed_left[l]), ""))
        items.append(("Avg per week · paid off ≈", f"{money(rate)} · {eta}", "small"))
    cards(items)

# ---------------------------------------------------------------- expenses
section("Expenses")
with st.expander("Add or remove an expense"):
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
            del_id = st.selectbox("Remove an expense", ["—"] + [f"{r['id']} · {r['description']} ${r['amount']:.2f}" for _, r in expenses.iterrows()])
            if del_id != "—" and st.button("Remove"):
                sb.table("expenses").delete().eq("id", int(del_id.split(" ·")[0])).execute()
                st.cache_data.clear()
                st.rerun()
if not expenses.empty:
    ex = expenses.copy()
    ex["recurring"] = ex["recurring"].fillna("one-off")
    st.dataframe(ex[["spent_on", "description", "amount", "recurring"]].rename(columns={"spent_on": "Date", "description": "Item", "amount": "Amount", "recurring": "Repeats"}),
                 use_container_width=True, hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="$%.2f")})

# ---------------------------------------------------------------- calendar
section("Calendar")
names = ["All accounts"] + [cfg[l]["nickname"] for l in logins]
months = sorted({(d.year, d.month) for d in trades["date"]})
if "cal_idx" not in st.session_state:
    st.session_state.cal_idx = len(months) - 1
r1 = st.columns([1, 1])
sel = r1[0].selectbox("Account", names, label_visibility="collapsed")
pick = r1[1].selectbox("Month", months, index=st.session_state.cal_idx, label_visibility="collapsed",
                       format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}")
if months.index(pick) != st.session_state.cal_idx:
    st.session_state.cal_idx = months.index(pick)
    st.rerun()
r2 = st.columns([1, 1])
if r2[0].button("◀ Prev", use_container_width=True, disabled=st.session_state.cal_idx == 0):
    st.session_state.cal_idx -= 1
    st.rerun()
if r2[1].button("Next ▶", use_container_width=True, disabled=st.session_state.cal_idx == len(months) - 1):
    st.session_state.cal_idx += 1
    st.rerun()

sel_login = None if sel == "All accounts" else logins[names.index(sel) - 1]
tsel = trades if sel_login is None else trades[trades["login"] == sel_login]
daily = tsel.groupby("date")["net"].sum()
year, month = months[st.session_state.cal_idx]
month_daily = daily[[d.year == year and d.month == month for d in daily.index]]
m_total = month_daily.sum()
base_for_pct = sum(cfg[l]["base"] for l in logins) if sel_login is None else cfg[sel_login]["base"]
col = GREEN if m_total >= 0 else RED
st.markdown(f"<div class='kw-monthline'><span style='color:{TEXT};font-size:17px'>{calendar.month_name[month]} {year}</span>"
            f"&nbsp;&nbsp;<span style='color:{col}'>{m_total:+,.2f}</span>"
            f"&nbsp;<span style='color:{col};opacity:0.7'>({m_total / base_for_pct * 100:+.2f}%)</span></div>", unsafe_allow_html=True)
tiles = "".join(f"<div class='kw-dow'>{n}</div>" for n in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
for week in calendar.Calendar(firstweekday=6).monthdayscalendar(year, month):
    for day in week:
        if day == 0:
            tiles += "<div class='kw-day empty'></div>"
            continue
        val = month_daily.get(date(year, month, day))
        if val is None:
            tiles += f"<div class='kw-day flat'><div class='n'>{day}</div></div>"
        else:
            cls = "pos" if val >= 0 else "neg"
            tiles += (f"<div class='kw-day {cls}'><div class='n'>{day}</div><div class='v'>{val:+,.0f}</div>"
                      f"<div class='p'>{val / base_for_pct * 100:+.2f}%</div></div>")
st.markdown(f"<div class='kw-cal'>{tiles}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- risk stats
section(f"Risk · {sel}")
wins = tsel[tsel["net"] > 0]
losses = tsel[tsel["net"] < 0]
n = len(tsel)
aw = wins["net"].mean() if len(wins) else 0
al = losses["net"].mean() if len(losses) else 0
pf = wins["net"].sum() / abs(losses["net"].sum()) if len(losses) and losses["net"].sum() != 0 else 0
weekly_sel = tsel.groupby("week")["net"].sum()
dd = 0.0
for wk, grp in tsel.sort_values("time").groupby("week"):
    dd = min(dd, grp["net"].cumsum().min())
streak = 0
for v in daily.sort_index(ascending=False):
    if v < 0:
        streak += 1
    else:
        break
cards([("Win rate", f"{len(wins) / n * 100 if n else 0:.0f}%", ""), ("Profit factor", f"{pf:.2f}", ""),
       ("Avg win / loss", f"{aw:,.0f} / {al:,.0f}", "small"), ("Trades", f"{n:,}", "")])
cards([("Worst day", money(daily.min() if len(daily) else 0), "neg"), ("Worst week", money(weekly_sel.min() if len(weekly_sel) else 0), "neg"),
       ("Deepest dip below base", money(dd), "neg" if dd < 0 else ""), ("Losing days in a row", f"{streak}", "neg" if streak else "")])

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
