import calendar
import math
import time
from datetime import date, datetime, timedelta

import extra_streamlit_components as stx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client

LOGO_URL = "https://raw.githubusercontent.com/jtudor7788/mt5-dashboard/main/logo.png?v=3"
ICON_URL = "https://raw.githubusercontent.com/jtudor7788/mt5-dashboard/main/apple-icon.png?v=3"

st.set_page_config(page_title="Kona Wolf Trading", page_icon=ICON_URL, layout="wide")

DAY_TZ = "America/New_York"
STALE_MINUTES = 20
MATCH_TOLERANCE = 5.00

# ---------------------------------------------------------------- palette
CARD, CARD2, LINE = "#111827", "#0D1420", "#1E2A40"
TEXT, MUTED, ACCENT = "#E8EDF7", "#7C8698", "#D4A843"
GREEN, RED, BLUE, PURPLE, GREY = "#2FBF71", "#E5484D", "#5B9CF6", "#A78BFA", "#64748B"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'IBM Plex Sans', sans-serif; }}
#MainMenu, footer {{ visibility: hidden; }}
header {{ visibility: hidden; height: 0; }}
header [data-testid="stSidebarCollapsedControl"],
header [data-testid="collapsedControl"],
header [data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] {{ visibility: visible !important; position: fixed; top: 10px; left: 10px; z-index: 999;
    background: {CARD}; border: 1px solid {LINE}; border-radius: 8px; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px; }}
* {{ font-variant-numeric: tabular-nums; }}

@keyframes kwfade {{ from {{ opacity:0; transform:translateY(4px); }} to {{ opacity:1; transform:none; }} }}
@keyframes kwpulse {{ 0% {{ box-shadow:0 0 0 0 rgba(47,191,113,0.5); }} 70% {{ box-shadow:0 0 0 7px rgba(47,191,113,0); }} 100% {{ box-shadow:0 0 0 0 rgba(47,191,113,0); }} }}

/* masthead */
.kw-mast {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;
            border-bottom:1px solid {LINE}; padding-bottom:16px; margin-bottom:20px; animation:kwfade .5s ease; }}
.kw-brand {{ display:flex; align-items:center; gap:14px; }}
.kw-logo {{ height:60px; width:auto; }}
.kw-mono {{ width:44px; height:44px; border:1px solid {ACCENT}; border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:17px; color:{ACCENT};
            background:linear-gradient(160deg, rgba(212,168,67,0.10), transparent 60%); letter-spacing:1px; }}
.kw-word {{ line-height:1.15; }}
.kw-word .a {{ font-size:19px; font-weight:600; color:{TEXT}; letter-spacing:0.14em; }}
.kw-word .b {{ font-size:10.5px; color:{MUTED}; letter-spacing:0.42em; }}
.kw-strip {{ display:flex; align-items:center; gap:22px; flex-wrap:wrap; }}
.kw-live {{ display:flex; align-items:center; gap:8px; font-size:12px; color:{MUTED}; }}
.kw-dot {{ width:8px; height:8px; border-radius:50%; background:{GREEN}; animation:kwpulse 2.2s infinite; }}
.kw-dot.bad {{ background:{RED}; animation:none; }}
.kw-sess {{ display:flex; gap:14px; font-size:11px; letter-spacing:0.1em; color:{MUTED}; }}
.kw-sess span b {{ font-weight:600; }}
.kw-sess .on {{ color:{GREEN}; }}
.kw-count {{ font-family:'IBM Plex Mono',monospace; font-size:12px; color:{TEXT};
             border:1px solid {LINE}; border-radius:8px; padding:7px 12px; background:{CARD2}; }}
.kw-count b {{ color:{ACCENT}; font-weight:600; }}

.kw-note {{ color:{MUTED}; font-size:12px; margin:0 0 6px; line-height:1.55; }}
.kw-section {{ font-size:13px; font-weight:600; color:{MUTED}; letter-spacing:0.18em; text-transform:uppercase; margin:30px 0 12px; }}
.kw-alert {{ background:#3A1B1F; border:1px solid #6A2A2A; color:#F5B5B8; border-radius:10px; padding:10px 14px; font-size:13px; margin-bottom:12px; }}

/* cards */
.kw-grid {{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:12px; margin-bottom:12px; }}
.kw-card {{ background:linear-gradient(180deg, rgba(255,255,255,0.025), transparent 34%), {CARD};
            border:1px solid {LINE}; border-top-color:#28374F; border-radius:12px; padding:14px 16px 12px;
            min-width:0; animation:kwfade .5s ease; }}
.kw-label {{ color:{MUTED}; font-size:10.5px; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:6px;
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kw-value {{ font-family:'IBM Plex Mono', monospace; font-size:23px; font-weight:600; color:{TEXT};
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kw-value.small {{ font-size:17px; }}
.kw-value.pos {{ color:{GREEN}; }}  .kw-value.neg {{ color:{RED}; }}
.kw-spark {{ margin-top:8px; height:26px; }}

/* account panels */
.kw-acct {{ background:linear-gradient(180deg, rgba(255,255,255,0.02), transparent 30%), {CARD};
            border:1px solid {LINE}; border-radius:12px; padding:16px 18px; margin-bottom:12px; animation:kwfade .5s ease; }}
.kw-acct .name {{ font-size:15px; font-weight:600; color:{TEXT}; }}
.kw-acct .tag {{ font-family:'IBM Plex Mono', monospace; font-size:11px; color:{ACCENT}; margin-left:8px; letter-spacing:0.08em; }}
.kw-acct .row {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(122px, 1fr)); gap:12px 18px; margin-top:12px; }}
.kw-acct .k {{ color:{MUTED}; font-size:10.5px; letter-spacing:0.08em; text-transform:uppercase; }}
.kw-acct .v {{ font-family:'IBM Plex Mono', monospace; font-size:17px; font-weight:600; color:{TEXT}; margin-top:2px; white-space:nowrap; }}
.kw-acct .v.pos {{ color:{GREEN}; }} .kw-acct .v.neg {{ color:{RED}; }}
.kw-bar {{ height:6px; background:{LINE}; border-radius:3px; margin-top:8px; overflow:hidden; }}
.kw-bar > div {{ height:100%; background:linear-gradient(90deg,{PURPLE},{BLUE}); }}

/* monthly returns grid */
.kw-mret {{ overflow-x:auto; border:1px solid {LINE}; border-radius:12px; background:{CARD}; animation:kwfade .5s ease; }}
.kw-mret table {{ border-collapse:collapse; width:100%; min-width:760px; font-family:'IBM Plex Mono',monospace; font-size:12.5px; }}
.kw-mret th {{ color:{MUTED}; font-weight:500; letter-spacing:0.08em; font-size:10.5px; padding:10px 8px; text-align:right; border-bottom:1px solid {LINE}; }}
.kw-mret th:first-child, .kw-mret td:first-child {{ text-align:left; padding-left:16px; color:{TEXT}; }}
.kw-mret td {{ padding:9px 8px; text-align:right; border-bottom:1px solid rgba(30,42,64,0.5); }}
.kw-mret tr:last-child td {{ border-bottom:none; }}
.kw-mret td.ytd {{ font-weight:600; border-left:1px solid {LINE}; }}

/* calendar */
.kw-cal {{ display:grid; grid-template-columns:repeat(7, minmax(0,1fr)); gap:7px; }}
.kw-dow {{ text-align:center; color:{MUTED}; font-size:10.5px; letter-spacing:0.1em; text-transform:uppercase; padding-bottom:5px; }}
.kw-day {{ border-radius:9px; padding:8px 4px; min-height:80px; text-align:center; font-family:'IBM Plex Mono', monospace;
           border:1px solid {LINE}; min-width:0; }}
.kw-day .n {{ font-size:11px; color:{MUTED}; }}
.kw-day .v {{ font-size:14px; font-weight:600; margin-top:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kw-day .p {{ font-size:10.5px; opacity:0.8; white-space:nowrap; }}
.kw-day.pos {{ background:#12352A; border-color:#1F5A45; color:{GREEN}; }}
.kw-day.neg {{ background:#3A1B1F; border-color:#6A2A2A; color:{RED}; }}
.kw-day.flat {{ background:{CARD}; color:{TEXT}; }}
.kw-day.empty {{ background:transparent; border-color:transparent; }}
.kw-monthline {{ font-family:'IBM Plex Mono', monospace; font-size:15px; margin:6px 0 10px; }}
div[data-testid="stSidebar"] {{ background:{CARD}; border-right:1px solid {LINE}; }}
.kw-refresh {{ position:fixed; bottom:18px; left:14px; z-index:998; width:46px; height:46px; border-radius:50%;
  background:{CARD}; border:1px solid {LINE}; color:{ACCENT}; display:flex; align-items:center; justify-content:center;
  font-size:22px; text-decoration:none; box-shadow:0 4px 14px rgba(0,0,0,0.45); }}
.kw-refresh:active {{ transform:scale(0.94); }}

@media (max-width: 700px) {{
  .block-container {{ padding-left:0.8rem; padding-right:0.8rem; padding-top:0.9rem; }}
  .kw-grid {{ grid-template-columns:repeat(2, minmax(0,1fr)); gap:9px; }}
  .kw-card {{ padding:11px 13px 9px; }}
  .kw-value {{ font-size:18px; }}  .kw-value.small {{ font-size:14px; }}
  .kw-acct .row {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
  .kw-acct .v {{ font-size:15px; }}
  .kw-cal {{ gap:3px; }}
  .kw-day {{ min-height:58px; padding:5px 2px; border-radius:6px; }}
  .kw-day .n {{ font-size:9.5px; }}
  .kw-day .v {{ font-size:10.5px; margin-top:3px; }}
  .kw-day .p {{ display:none; }}
  .kw-dow {{ font-size:9px; }}
  .kw-sess {{ display:none; }}
  .kw-logo {{ height:42px; width:auto; }}
  div[data-testid="stHorizontalBlock"] {{ flex-wrap:nowrap !important; gap:6px !important; }}
  div[data-testid="stHorizontalBlock"] > div {{ min-width:0 !important; flex:1 1 0 !important; }}
}}
</style>
""", unsafe_allow_html=True)

import streamlit.components.v1 as _components
_components.html(f"""<script>
try {{
  const d = (window.top || window.parent).document;
  d.querySelectorAll("link[rel='apple-touch-icon'], link[rel='icon']").forEach(function(l) {{ l.remove(); }});
  ["apple-touch-icon", "apple-touch-icon-precomposed", "icon"].forEach(function(r) {{
    const l = d.createElement("link");
    l.rel = r; l.sizes = "512x512"; l.href = "{ICON_URL}";
    d.head.appendChild(l);
  }});
}} catch (e) {{}}
</script>""", height=0)

sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

# ---------------------------------------------------------------- login (with remember-me cookie)
COOKIE = "kw_refresh"
cookies = stx.CookieManager(key="kw_cookies")


def remember(session):
    cookies.set(COOKIE, session.refresh_token,
                expires_at=datetime.now() + timedelta(days=30), key="kw_set")


if "session" not in st.session_state:
    all_cookies = cookies.get_all(key="kw_all")
    if all_cookies is None:
        started = st.session_state.setdefault("cookie_wait_start", time.time())
        if time.time() - started < 4:
            st.markdown("<div style='text-align:center;margin-top:35vh;color:#7C8698;font-size:14px'>Signing in…</div>",
                        unsafe_allow_html=True)
            st.stop()
    saved = (all_cookies or {}).get(COOKIE)
    if saved:
        try:
            res = sb.auth.refresh_session(saved)
            if res and res.session:
                st.session_state.session = res.session
                remember(res.session)
        except Exception:
            pass

if "session" not in st.session_state:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(f"<div style='text-align:center;margin-bottom:10px'><img src='{LOGO_URL}' style='width:340px;max-width:88%'></div>"
                    "<div class='kw-note' style='text-align:center'>Sign in to view the accounts</div>", unsafe_allow_html=True)
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Sign in", use_container_width=True):
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.session = res.session
                remember(res.session)
                time.sleep(1.5)
                st.rerun()
            except Exception:
                st.error("Email or password didn't match.")
    st.stop()

TOKEN = st.session_state.session.access_token
sb.postgrest.auth(TOKEN)

if st.query_params.get("r"):
    st.cache_data.clear()
    st.query_params.clear()


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


# Newer rows carry a measured true-UTC stamp from the collector; older rows are
# broker-clock and get the legacy -7h correction. Days are Eastern, midnight to midnight.
raw = pd.to_datetime(deals["time"], utc=True)
if "time_utc" in deals.columns:
    fixed = pd.to_datetime(deals["time_utc"], utc=True, errors="coerce")
else:
    fixed = pd.Series(pd.NaT, index=deals.index, dtype="datetime64[ns, UTC]")
deals["time"] = fixed.fillna(raw - pd.Timedelta(hours=7)).dt.tz_convert(DAY_TZ)
deals["net"] = deals["profit"].fillna(0) + deals["commission"].fillna(0) + deals["swap"].fillna(0)
deals["date"] = deals["time"].dt.date
deals["week"] = deals["date"].map(week_of)
trades = deals[deals["entry"].isin([1, 3]) & deals["type"].isin([0, 1])].copy()
cash = deals[deals["type"] == 2].copy()
withdrawals = cash[cash["net"] < 0]

snaps = snaps.drop_duplicates("login") if not snaps.empty else snaps
latest = {r["login"]: r for _, r in snaps.iterrows()}

now_et = pd.Timestamp.now(DAY_TZ)
today = now_et.date()
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
        "kolby_pct": float(row.get("kolby_pct") or 0),
        "prior_kolby": float(row.get("prior_kolby") or 0),
    }
logins = sorted(cfg, key=lambda l: (not cfg[l]["is_master"], cfg[l]["nickname"]))
master = next((l for l in logins if cfg[l]["is_master"]), logins[0])
BASE_TOTAL = sum(cfg[l]["base"] for l in logins)

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
    for c in ["gross", "expenses", "seed", "ben", "jesse", "kolby"]:
        if c in ledger.columns:
            ledger[c] = ledger[c].astype(float)
        else:
            ledger[c] = 0.0
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
        w = withdrawals[(withdrawals["login"] == login) & (withdrawals["date"] >= fri) & (withdrawals["date"] < fri + timedelta(days=7))]
        withdrawn = -w["net"].sum()
        tracked = wk >= c["started_on"]
        key = (wk, login)
        if key in frozen:
            f = frozen[key]
            exp, seed_pay, ben, jesse, kolby = f["expenses"], f["seed"], f["ben"], f["jesse"], f.get("kolby", 0.0)
            gross = f["gross"]
            seed_left = max(seed_left - seed_pay, 0.0)
            carry = 0.0
            status = "paid"
        elif not tracked:
            exp = seed_pay = ben = jesse = kolby = 0.0
            status = "before tracking"
        else:
            exp = 0.0
            if c["pays_expenses"]:
                exp = WEEKLY_RECURRING + oneoff.loc[oneoff["week"] == wk, "amount"].sum()
            base = gross - exp + carry
            if base <= 0:
                carry, seed_pay, ben, jesse, kolby = base, 0.0, 0.0, 0.0, 0.0
            else:
                carry = 0.0
                kolby = base * c["kolby_pct"]
                seed_pay = min(base * 0.5, seed_left)
                seed_left -= seed_pay
                rest = base - kolby - seed_pay
                ben = jesse = rest / 2
            if wk == this_week:
                status = "in progress"
            elif withdrawn == 0 and today < fri + timedelta(days=7):
                status = "pending"
            elif abs(withdrawn - (ben + jesse + exp + seed_pay)) > MATCH_TOLERANCE:
                status = "⚠ mismatch"
            else:
                status = "✓ matched"
        if status == "paid":
            expected = ben + jesse + kolby + exp + seed_pay
            if withdrawn == 0 and today < fri + timedelta(days=7):
                status = "paid · pending"
            elif abs(withdrawn - expected) > MATCH_TOLERANCE:
                status = "paid · ⚠ mismatch"
            else:
                status = "paid ✓"
        out.append({"week": wk, "login": login, "account": c["nickname"], "gross": gross, "expenses": exp,
                    "seed": seed_pay, "ben": ben, "jesse": jesse, "kolby": kolby, "ben_total": ben + exp,
                    "expected_withdrawal": ben + jesse + kolby + exp + seed_pay, "withdrawn": withdrawn,
                    "status": status, "tracked": tracked, "in_progress": wk == this_week, "frozen": key in frozen})
    return pd.DataFrame(out), seed_left


payouts, seed_left = {}, {}
for l in logins:
    payouts[l], seed_left[l] = compute_payouts(l)
allp = pd.concat(payouts.values(), ignore_index=True) if payouts else pd.DataFrame()
cur = allp[allp["week"] == this_week] if not allp.empty else pd.DataFrame()
tracked = allp[allp["tracked"]] if not allp.empty else pd.DataFrame()

daily_all = trades.groupby("date")["net"].sum().sort_index()


# ---------------------------------------------------------------- helpers
def money(v):
    return f"{v:,.2f}"


def sgn(v):
    return "pos" if v > 0 else ("neg" if v < 0 else "")


def spark(values, color=BLUE, w=120, h=24):
    vals = [float(v) for v in values if v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{i / (len(vals) - 1) * w:.1f},{h - (v - lo) / rng * (h - 3) - 1.5:.1f}" for i, v in enumerate(vals))
    return (f"<div class='kw-spark'><svg width='100%' height='{h}' viewBox='0 0 {w} {h}' preserveAspectRatio='none'>"
            f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='1.6' stroke-linejoin='round' stroke-linecap='round'/>"
            f"</svg></div>")


def cards(items):
    html = ""
    for it in items:
        l, v, c = it[0], it[1], it[2]
        sp = it[3] if len(it) > 3 else ""
        html += f"<div class='kw-card'><div class='kw-label'>{l}</div><div class='kw-value {c}'>{v}</div>{sp}</div>"
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
    lines = [f"Kona Wolf Trading - week of {wk:%b %d, %Y} (payout Fri {wk + timedelta(days=4):%b %d})", ""]
    for _, r in rows.iterrows():
        lines.append(f"{r['account']} (#{r['login']})")
        lines.append(f"  Gross profit:        ${r['gross']:,.2f}")
        if r["seed"]:
            lines.append(f"  Seed -> {cfg[r['login']]['seed_holder']}:       ${r['seed']:,.2f}")
        lines.append(f"  Ben/Jesse split each: ${r['ben'] + r['expenses'] / 2:,.2f}")
        if r["expenses"]:
            lines.append(f"  Expenses (Ben card): ${r['expenses']:,.2f}  -> Jesse pays Ben half: ${r['expenses'] / 2:,.2f}")
        lines.append(f"  Ben receives:        ${r['ben'] + r['expenses']:,.2f}")
        lines.append(f"  Jesse receives:      ${r['jesse']:,.2f}")
        if r["kolby"]:
            lines.append(f"  Kolby receives:      ${r['kolby']:,.2f}")
        lines.append(f"  Withdraw total:      ${r['expected_withdrawal']:,.2f}")
        lines.append("")
    if len(rows) > 1:
        lines.append(f"ALL ACCOUNTS - Ben ${(rows['ben'] + rows['expenses']).sum():,.2f} / Jesse ${rows['jesse'].sum():,.2f} / Seed ${rows['seed'].sum():,.2f} / Withdraw ${rows['expected_withdrawal'].sum():,.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"<div class='kw-label'>Signed in</div><div style='font-size:13px;color:{TEXT}'>{st.session_state.session.user.email}</div>",
                unsafe_allow_html=True)
    sync_times = [pd.to_datetime(r["time"]) for r in latest.values()]
    last_sync_ts = max(sync_times) if sync_times else None
    last_sync = last_sync_ts.tz_convert(DAY_TZ).strftime("%b %d, %I:%M %p") if last_sync_ts is not None else "—"
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
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    with st.expander("Change password"):
        np1 = st.text_input("New password", type="password", key="np1")
        np2 = st.text_input("Repeat it", type="password", key="np2")
        if st.button("Update password", use_container_width=True):
            if len(np1) < 8:
                st.error("Use at least 8 characters.")
            elif np1 != np2:
                st.error("Passwords don't match.")
            else:
                try:
                    sb.auth.update_user({"password": np1})
                    st.success("Password updated.")
                except Exception as ex:
                    st.error(f"Couldn't update: {ex}")
    if st.button("Sign out", use_container_width=True):
        cookies.delete(COOKIE, key="kw_del")
        del st.session_state.session
        time.sleep(1.0)
        st.rerun()

# ---------------------------------------------------------------- masthead
age_min = (now_utc - last_sync_ts).total_seconds() / 60 if last_sync_ts is not None else 9999
fresh = age_min <= STALE_MINUTES
h = now_et.hour + now_et.minute / 60
wd = now_et.weekday()
fx_open = not (wd == 5 or (wd == 6 and h < 17) or (wd == 4 and h >= 17))
tokyo = fx_open and (h >= 19 or h < 4)
london = fx_open and (3 <= h < 11.5)
ny = fx_open and (8 <= h < 17)
payout_dt = pd.Timestamp(this_week + timedelta(days=4), tz=DAY_TZ) + pd.Timedelta(hours=17)
if now_et > payout_dt:
    payout_dt += pd.Timedelta(days=7)
secs = (payout_dt - now_et).total_seconds()
countdown = f"{int(secs // 86400)}d {int(secs % 86400 // 3600):02d}h"


def sess(name, on):
    return f"<span class='{'on' if on else ''}'><b>{name}</b> {'●' if on else '○'}</span>"


st.markdown("<a class='kw-refresh' href='?r=1' title='Refresh data'>↻</a>", unsafe_allow_html=True)
st.markdown(f"""
<div class='kw-mast'>
  <div class='kw-brand'>
    <img src='{LOGO_URL}' class='kw-logo' alt='Kona Wolf Trading Company'>
  </div>
  <div class='kw-strip'>
    <div class='kw-sess'>{sess('TOKYO', tokyo)}{sess('LONDON', london)}{sess('NEW YORK', ny)}</div>
    <div class='kw-live'><div class='kw-dot {'bad' if not fresh else ''}'></div>{'LIVE' if fresh else 'STALE'} · synced {int(age_min)}m ago</div>
    <div class='kw-count'>Payout in <b>{countdown}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

if not fresh:
    st.markdown(f"<div class='kw-alert'>⚠ Data is {age_min:.0f} minutes old. The VPS collector hasn't synced since {last_sync} ET — check that MT5 is logged in and the scheduled task is running.</div>",
                unsafe_allow_html=True)

# ---------------------------------------------------------------- header cards: this week
g = cur["gross"].sum() if not cur.empty else 0
e = cur["expenses"].sum() if not cur.empty else 0
sd = cur["seed"].sum() if not cur.empty else 0
k = cur["kolby"].sum() if not cur.empty else 0
any_kolby = any(cfg[l]["kolby_pct"] > 0 for l in logins)
seed_holders = " / ".join(sorted({cfg[l]["seed_holder"] for l in logins if cfg[l]["seed"] > 0 and seed_left[l] > 0})) or "—"
b = cur["ben"].sum() if not cur.empty else 0
j = cur["jesse"].sum() if not cur.empty else 0
half = e / 2
share = b + half

wk_days = daily_all[daily_all.index >= this_week]
month_start = today.replace(day=1)
d_today = daily_all.get(today, 0)
d_month = daily_all[daily_all.index >= month_start].sum()
today_trades = trades[trades["date"] == today].sort_values("time")
bal_hist = deals[deals["type"].isin([0, 1, 2])].groupby("date")["net"].sum().cumsum().tail(30)
week_spark = spark(wk_days.cumsum(), GREEN if g >= 0 else RED)
today_spark = spark(today_trades["net"].cumsum(), GREEN if d_today >= 0 else RED)

st.markdown(f"<div class='kw-note' style='margin-bottom:10px'>Week of {this_week:%B %d} · {len(logins)} account{'s' if len(logins) != 1 else ''} · payout Friday {this_week + timedelta(days=4):%B %d}</div>", unsafe_allow_html=True)
cards([("Today", money(d_today), sgn(d_today), today_spark),
       ("Gross this week", money(g), sgn(g), week_spark),
       ("This month", money(d_month), sgn(d_month)),
       (f"Seed → {seed_holders}", money(sd), "")])
cards([("Expenses on Ben's card", money(e), ""),
       ("Jesse → Ben for half", money(half), ""),
       ("Ben receives", money(b + e), sgn(b + e)),
       ("Jesse receives", money(j), sgn(j))])
if any_kolby:
    cards([("Kolby receives", money(k), sgn(k)),
           ("Ben / Jesse split each", money(share), sgn(share))])
st.markdown(f"<div class='kw-note'>Profit splits 50/50 at {money(share)} each. Expenses of {money(e)} were paid on Ben's card, so Jesse's half ({money(half)}) "
            f"moves from Jesse's share to Ben. Ben receives {money(share)} + {money(half)} = {money(b + e)}. Jesse receives {money(share)} − {money(half)} = {money(j)}.</div>",
            unsafe_allow_html=True)

# ---------------------------------------------------------------- totals
prior_ben = sum(cfg[l]["prior_ben"] for l in logins)
prior_jesse = sum(cfg[l]["prior_jesse"] for l in logins)
prior_seed = sum(cfg[l]["prior_seed"] for l in logins)
prior_kolby = sum(cfg[l]["prior_kolby"] for l in logins)
if not tracked.empty or prior_ben or prior_jesse or prior_seed:
    section("Totals to date")
    tb = (tracked["ben"] + tracked["expenses"]).sum() if not tracked.empty else 0
    tj = tracked["jesse"].sum() if not tracked.empty else 0
    ts_ = tracked["seed"].sum() if not tracked.empty else 0
    te = tracked["expenses"].sum() if not tracked.empty else 0
    tg = tracked["gross"].sum() if not tracked.empty else 0
    cards([("Ben · all time", money(prior_ben + tb), "pos"),
           ("Jesse · all time", money(prior_jesse + tj), "pos"),
           ("Seed repaid to date", money(prior_seed + ts_), ""),
           ("Expenses on Ben's card · since ledger", money(te), "")])
    tk = tracked["kolby"].sum() if not tracked.empty else 0
    r = [("Ben · since ledger", money(tb), "pos"),
         ("Jesse · since ledger", money(tj), "pos")]
    if any_kolby or tk or prior_kolby:
        r.append(("Kolby · all time", money(prior_kolby + tk), "pos"))
    r.append(("Gross · since ledger", money(tg), sgn(tg)))
    cards(r)
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

# ---------------------------------------------------------------- performance: equity + drawdown, monthly grid
section("Performance")
cum = daily_all.cumsum()
peak = cum.cummax()
fig = go.Figure()
fig.add_scatter(x=list(peak.index), y=list(peak.values), mode="lines",
                line=dict(color="rgba(212,168,67,0.45)", width=1, dash="dot"), name="High-water mark",
                hovertemplate="HWM %{y:,.0f}<extra></extra>")
fig.add_scatter(x=list(cum.index), y=list(cum.values), mode="lines",
                line=dict(color=BLUE, width=2), fill="tonexty", fillcolor="rgba(229,72,77,0.12)", name="Cumulative P&L",
                hovertemplate="%{x|%b %d}<br>%{y:,.0f}<extra></extra>")
fig.add_annotation(x=peak.index[-1], y=peak.iloc[-1], text=f"HWM {peak.iloc[-1]:,.0f}",
                   showarrow=False, yshift=12, font=dict(size=11, color=ACCENT))
st.plotly_chart(chart_layout(fig, 360), use_container_width=True, config={"displayModeBar": False})
st.markdown("<div class='kw-note'>Blue line is cumulative realised P&L across all accounts; the shaded band is drawdown from the high-water mark.</div>", unsafe_allow_html=True)

# monthly returns grid
mret = trades.copy()
mret["y"] = mret["time"].dt.year
mret["m"] = mret["time"].dt.month
grid = mret.groupby(["y", "m"])["net"].sum().unstack(fill_value=float("nan"))
rows_html = ""
for y in sorted(grid.index):
    cells = ""
    ytd = 0.0
    for m in range(1, 13):
        v = grid.loc[y].get(m)
        if v is None or v != v:
            cells += "<td style='color:#3A465C'>—</td>"
        else:
            pct = v / BASE_TOTAL * 100
            ytd += pct
            a = min(abs(pct) / 8, 1) * 0.5
            bg = f"rgba(47,191,113,{a:.2f})" if pct >= 0 else f"rgba(229,72,77,{a:.2f})"
            fg = GREEN if pct >= 0 else RED
            cells += f"<td style='background:{bg};color:{fg}'>{pct:+.1f}%</td>"
    fg = GREEN if ytd >= 0 else RED
    rows_html += f"<tr><td>{y}</td>{cells}<td class='ytd' style='color:{fg}'>{ytd:+.1f}%</td></tr>"
mons = "".join(f"<th>{m}</th>" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
st.markdown(f"<div class='kw-mret'><table><thead><tr><th>Year</th>{mons}<th>YTD</th></tr></thead><tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True)
st.markdown(f"<div class='kw-note'>Monthly return on trading capital (${BASE_TOTAL:,.0f} base).</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- friday summary
section("Friday summary")
week_opts = sorted(tracked["week"].unique(), reverse=True) if not tracked.empty else [this_week]
wsel = st.selectbox("Week", week_opts, format_func=lambda w: f"Week of {w:%b %d}" + (" (in progress)" if w == this_week else ""), label_visibility="collapsed")
st.code(summary_text(wsel), language=None)
st.markdown("<div class='kw-note'>Tap the copy icon in the top-right of the box, then paste into a text to Ben or Donna.</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- weekly payouts chart
section("Weekly payouts")
if not tracked.empty:
    wk_sum = tracked.groupby("week")[["jesse", "ben", "kolby", "seed", "expenses"]].sum().sort_index().tail(16)
    x = [f"{w:%b %d}" for w in wk_sum.index]
    fig = go.Figure()
    for col, name, color in [("jesse", "Jesse", BLUE), ("ben", "Ben", GREEN), ("kolby", "Kolby", ACCENT), ("seed", "Seed", PURPLE), ("expenses", "Expenses", GREY)]:
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
    show = hist[["Week", "account", "status", "gross", "seed", "expenses", "jesse_to_ben", "ben_total", "jesse", "kolby", "expected_withdrawal", "withdrawn"]].rename(columns={
        "account": "Account", "status": "Status", "gross": "Gross", "seed": "Seed", "expenses": "Expenses (Ben's card)",
        "jesse_to_ben": "Jesse → Ben", "ben_total": "Ben receives", "jesse": "Jesse receives", "kolby": "Kolby receives",
        "expected_withdrawal": "Should withdraw", "withdrawn": "Withdrawn (MT5)"})
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={k: st.column_config.NumberColumn(format="dollar") for k in show.columns if k not in ("Week", "Account", "Status")})

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
                                                "seed": float(r["seed"]), "ben": float(r["ben"]), "jesse": float(r["jesse"]), "kolby": float(r["kolby"]),
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
                 use_container_width=True, hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="dollar")})

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
base_for_pct = BASE_TOTAL if sel_login is None else cfg[sel_login]["base"]
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

# ---------------------------------------------------------------- risk & edge
section(f"Risk & edge · {sel}")
wins = tsel[tsel["net"] > 0]
losses = tsel[tsel["net"] < 0]
n = len(tsel)
aw = wins["net"].mean() if len(wins) else 0
al = losses["net"].mean() if len(losses) else 0
pf = wins["net"].sum() / abs(losses["net"].sum()) if len(losses) and losses["net"].sum() != 0 else 0
expectancy = tsel["net"].mean() if n else 0
weekly_sel = tsel.groupby("week")["net"].sum()
wret = weekly_sel / base_for_pct
sharpe = (wret.mean() / wret.std() * math.sqrt(52)) if len(wret) > 2 and wret.std() > 0 else 0
dd = 0.0
for wk, grp in tsel.sort_values("time").groupby("week"):
    dd = min(dd, grp["net"].cumsum().min())
streak = 0
for v in daily.sort_index(ascending=False):
    if v < 0:
        streak += 1
    else:
        break
best_streak = cur_streak = 0
for v in daily.sort_index():
    cur_streak = cur_streak + 1 if v > 0 else 0
    best_streak = max(best_streak, cur_streak)
cum_sel = daily.cumsum()
peak_sel = cum_sel.cummax()
under = cum_sel - peak_sel
max_dd_curve = under.min() if len(under) else 0
cards([("Win rate", f"{len(wins) / n * 100 if n else 0:.0f}%", ""),
       ("Profit factor", f"{pf:.2f}", ""),
       ("Expectancy / trade", f"{expectancy:+,.2f}", sgn(expectancy)),
       ("Sharpe (weekly, ann.)", f"{sharpe:.2f}", "")])
cards([("Avg win / loss", f"{aw:,.0f} / {al:,.0f}", "small"),
       ("Best green streak", f"{best_streak} days", "pos"),
       ("Max drawdown (curve)", money(max_dd_curve), "neg" if max_dd_curve < 0 else ""),
       ("Losing days in a row", f"{streak}", "neg" if streak else "")])
cards([("Worst day", money(daily.min() if len(daily) else 0), "neg"),
       ("Worst week", money(weekly_sel.min() if len(weekly_sel) else 0), "neg"),
       ("Deepest dip below base", money(dd), "neg" if dd < 0 else ""),
       ("Trades", f"{n:,}", "")])

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

st.markdown(f"<div style='border-top:1px solid {LINE};margin-top:36px;padding-top:14px;color:{MUTED};font-size:11px;letter-spacing:0.08em'>"
            f"KONA WOLF TRADING · internal use only · data via MT5 #{', #'.join(str(l) for l in logins)} · synced {last_sync} ET</div>",
            unsafe_allow_html=True)
