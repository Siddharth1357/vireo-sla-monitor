import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vireo SLA Monitor", layout="wide")
st.title("Vireo Audio — First-Response SLA Monitor")
st.caption("Weekly SLA reporting by resolving agent, historical shift, and channel. Times shown in IST.")
SLA = {"chat": 15, "voice": 120, "social": 240, "email": 480}
CREDIT = 350

with st.sidebar:
    tf = st.file_uploader("Upload tickets.csv", type="csv")
    af = st.file_uploader("Upload agents.csv", type="csv")
    api_key = st.text_input("Optional OpenAI API key for narrative", type="password")

if not tf or not af:
    st.info("Upload tickets.csv and agents.csv to begin.")
    st.markdown("**SLA targets:** chat 15 min · voice 2 h · social 4 h · email 8 h")
    st.stop()

try:
    t = pd.read_csv(tf)
    a = pd.read_csv(af)
    need_t = {"ticket_id","created_at","first_response_at","resolved_at","channel","agent_id","source_system","csat_score"}
    need_a = {"agent_id","name","team","shift","from_date","to_date"}
    if not need_t.issubset(t.columns): raise ValueError(f"Missing ticket columns: {sorted(need_t-set(t.columns))}")
    if not need_a.issubset(a.columns): raise ValueError(f"Missing roster columns: {sorted(need_a-set(a.columns))}")

    for c in ["created_at","first_response_at","resolved_at"]:
        t[c] = pd.to_datetime(t[c], utc=True, errors="coerce").dt.tz_convert("Asia/Kolkata")
    legacy_zero = t["source_system"].eq("legacy_fd") & pd.to_numeric(t["csat_score"], errors="coerce").eq(0)
    t.loc[legacy_zero, "csat_score"] = pd.NA
    t["_rank"] = t["source_system"].map({"legacy_fd": 0, "helpdesk": 1}).fillna(-1)
    t = t.sort_values("_rank").drop_duplicates("ticket_id", keep="last").drop(columns="_rank").copy()
    t["channel"] = t["channel"].astype(str).str.lower().str.strip()
    t["sla_minutes"] = t["channel"].map(SLA)
    t["response_minutes"] = (t["first_response_at"]-t["created_at"]).dt.total_seconds()/60
    t["sla_breach"] = t["response_minutes"] > t["sla_minutes"]

    a["from_date"] = pd.to_datetime(a["from_date"], errors="coerce").dt.date
    a["to_date"] = pd.to_datetime(a["to_date"], errors="coerce").dt.date
    t["resolution_date"] = t["resolved_at"].dt.date
    m = t.merge(a[["agent_id","name","team","shift","from_date","to_date"]], on="agent_id", how="left")
    active = (m["resolution_date"].notna() & m["from_date"].notna() &
              (m["resolution_date"] >= m["from_date"]) &
              (m["to_date"].isna() | (m["resolution_date"] <= m["to_date"])))
    m = m.loc[active].copy()
    m["week_start"] = (m["created_at"].dt.normalize()-pd.to_timedelta(m["created_at"].dt.dayofweek, unit="D")).dt.strftime("%Y-%m-%d")
except Exception as e:
    st.error(f"Could not process files: {e}")
    st.stop()

weeks = sorted(m["week_start"].dropna().unique())
shifts = sorted(m["shift"].dropna().unique())
channels = sorted(m["channel"].dropna().unique())
with st.sidebar:
    sw = st.multiselect("Week start (Monday, IST)", weeks, default=weeks, key="week_filter_all")
    ss = st.multiselect("Shift", shifts, default=shifts)
    sc = st.multiselect("Channel", channels, default=channels)
f = m[m["week_start"].isin(sw) & m["shift"].isin(ss) & m["channel"].isin(sc)].copy()
n = f["ticket_id"].nunique()
b = int(f["sla_breach"].sum())
rate = (100*b/n) if n else 0
credit = b*CREDIT
c1,c2,c3,c4 = st.columns(4)
c1.metric("Tickets", f"{n:,}")
c2.metric("SLA breaches", f"{b:,}")
c3.metric("Breach rate", f"{rate:.2f}%")
c4.metric("Policy credit estimate", f"₹{credit:,}")
st.caption("Report population: tickets with a resolution timestamp and a matching roster assignment. ₹350 is a policy estimate, not verified Finance expenditure.")

weekly = f.groupby(["week_start","agent_id","name","team","shift"], dropna=False).agg(
    tickets=("ticket_id","nunique"), breaches=("sla_breach","sum"), avg_response_minutes=("response_minutes","mean")
).reset_index()
if not weekly.empty:
    weekly["breach_rate_pct"] = (100*weekly["breaches"]/weekly["tickets"]).round(2)
    weekly["avg_response_minutes"] = weekly["avg_response_minutes"].round(2)
    weekly["estimated_credit_inr"] = weekly["breaches"]*CREDIT
st.subheader("Weekly breaches by resolving agent and shift")
st.dataframe(weekly.sort_values(["week_start","breaches"], ascending=[False,False]), use_container_width=True, hide_index=True)
st.download_button("Download weekly report CSV", weekly.to_csv(index=False).encode(), "weekly_sla_report.csv", "text/csv")

st.subheader("Channel summary")
ch = f.groupby("channel").agg(tickets=("ticket_id","nunique"), breaches=("sla_breach","sum"), avg_response_minutes=("response_minutes","mean")).reset_index()
if not ch.empty:
    ch["breach_rate_pct"] = (100*ch["breaches"]/ch["tickets"]).round(2)
    ch["estimated_credit_inr"] = ch["breaches"]*CREDIT
    st.dataframe(ch.sort_values("breach_rate_pct", ascending=False), use_container_width=True, hide_index=True)
    st.bar_chart(ch.set_index("channel")["breach_rate_pct"])
    st.download_button("Download channel CSV", ch.to_csv(index=False).encode(), "channel_sla_report.csv", "text/csv")

checks = [
    ("Unique ticket IDs after dedup", t["ticket_id"].is_unique, f"{t['ticket_id'].nunique():,} IDs"),
    ("First-response timestamps present", t["first_response_at"].notna().all(), f"{t['first_response_at'].isna().sum():,} missing"),
    ("No negative response duration", not (t["response_minutes"]<0).any(), f"{(t['response_minutes']<0).sum():,} negative"),
    ("SLA targets present", t["sla_minutes"].notna().all(), f"{t['sla_minutes'].isna().sum():,} missing"),
    ("Roster mapped for report rows", m["shift"].notna().all(), f"{len(m):,} rows"),
    ("Weekly grouping unique", not weekly.duplicated(["week_start","agent_id","name","team","shift"]).any(), f"{len(weekly):,} rows")
]
v = pd.DataFrame(checks, columns=["check","passed","detail"])
v["status"] = v["passed"].map({True:"PASS",False:"REVIEW"})
with st.expander("Validation evidence"):
    st.dataframe(v, use_container_width=True, hide_index=True)
    st.write(f"Deduplicated tickets: {t['ticket_id'].nunique():,}; no resolution timestamp: {t['resolved_at'].isna().sum():,}; IVR marker records: {t['customer_message'].astype(str).str.startswith('[IVR transcript]').sum() if 'customer_message' in t else 'column unavailable'}.")
    st.download_button("Download validation CSV", v.to_csv(index=False).encode(), "validation_evidence.csv", "text/csv")

st.subheader("Operations narrative")
narrative = (f"Selected population: {n:,} tickets; {b:,} first-response SLA breaches ({rate:.2f}%). "
             f"Policy-based credit estimate: ₹{credit:,} at ₹350 per breach. This is not actual Finance spend. "
             "Review recurring channel, week, and shift patterns in context; these descriptive results do not establish individual fault or causation.")
if st.button("Generate summary"):
    if api_key:
        try:
            from openai import OpenAI
            response = OpenAI(api_key=api_key).responses.create(
                model="gpt-4.1-mini",
                input="Write a neutral operations summary from these aggregate metrics. Do not blame individuals, infer causation, or call estimates actual spend. Recommend no hiring.\n"+narrative
            )
            st.write(response.output_text)
            st.caption("Optional AI summary. Review before sharing.")
        except Exception as e:
            st.warning(f"AI API unavailable; showing deterministic summary. Details: {e}")
            st.write(narrative)
    else:
        st.write(narrative)
        st.caption("Rule-based summary; no API key used.")
