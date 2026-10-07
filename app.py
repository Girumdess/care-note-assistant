"""CareScribe AI — client-centric compliant care documentation with PHI protection,
weekly highlight summaries, note history, and per-client health overviews.

All demo data is synthetic.
"""
import os
import re
import json
from pathlib import Path
from datetime import date, timedelta
import streamlit as st

from care_assistant import store

st.set_page_config(page_title="CareScribe AI", page_icon="🩺",
                   layout="wide", initial_sidebar_state="expanded")
store.seed_if_empty()

try:
    from streamlit_mic_recorder import speech_to_text  # noqa: F401  (availability check)
    HAS_STT = True
except Exception:
    HAS_STT = False

ROOT = Path(__file__).parent

@st.cache_data
def load_demo_insights():
    p = ROOT / "assets" / "demo_insights.json"
    return json.load(open(p)) if p.exists() else {}

@st.cache_data
def load_eval():
    p = ROOT / "reports" / "eval_results.json"
    return json.load(open(p)) if p.exists() else None

DEMO = load_demo_insights()
EVAL = load_eval()

# ----------------------------- styling -----------------------------
st.html("""
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap");
/* Layout idea: a clinical chart. Notes sit on form paper under an ink rule, PHI is blacked out
   like a released record, numbers live in a hairline spec strip. */
:root {
  --ink: #14213d; --ink-2: #4a5568; --muted: #5d6878; --paper: #ffffff;
  --chart: #f4f6f9; --rule: #dfe4ec; --rule-soft: #ebeef3;
  --accent: #1e4d8c; --redact: #111827; --warn-bg: #fdf6e7; --warn-line: #e8c77a; --warn-ink: #6b4a0c;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --body: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
html, body, [class*="css"], .stMarkdown, .stTextInput, .stTextArea, button { font-family: var(--body); }
.block-container { padding-top: 5rem; max-width: 1120px; }
h1, h2, h3 { font-family: var(--display); letter-spacing: -0.01em; }

.chart-head { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 1rem 2rem;
  align-items: end; padding-bottom: 1rem; border-bottom: 2px solid var(--ink); margin-bottom: 0; }
.chart-head .kicker { font: 500 .74rem/1 var(--mono); letter-spacing: .14em; text-transform: uppercase;
  color: var(--muted); margin: 0 0 .5rem; }
.chart-head h1 { font: 600 2.35rem/1 var(--display); color: var(--ink); margin: 0; padding: 0; }
.chart-head p { color: var(--ink-2); font-size: 1rem; margin: .55rem 0 0; max-width: 58ch; }
.spec { display: grid; grid-template-columns: repeat(3, minmax(0, auto)); border: 1px solid var(--rule);
  border-radius: 4px; background: var(--paper); }
.spec div { padding: .55rem .9rem; border-left: 1px solid var(--rule); }
.spec div:first-child { border-left: none; }
.spec b { display: block; font: 500 1.35rem/1.1 var(--mono); color: var(--ink); font-variant-numeric: tabular-nums; }
.spec span { font: 500 .68rem/1.3 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
@media (max-width: 760px) { .chart-head { grid-template-columns: minmax(0,1fr); } }

.notice { display: flex; gap: .7rem; align-items: baseline; background: var(--warn-bg);
  border-bottom: 1px solid var(--warn-line); color: var(--warn-ink); padding: .55rem .9rem;
  font-size: .86rem; margin: 0 0 1.1rem; }
.notice b { flex: none; font: 600 .7rem/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; }

.note-output { background: var(--paper); border: 1px solid var(--rule); border-top: 2px solid var(--ink);
  border-radius: 0 0 4px 4px; padding: .9rem 1.1rem; line-height: 1.7; font-size: .97rem; color: var(--ink);
  white-space: pre-wrap; margin: .3rem 0; max-width: 75ch; }
.redact { background: var(--redact); color: #fff; padding: .05rem .4rem; border-radius: 2px;
  font: 500 .66rem/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; vertical-align: .08em; }
.phi-chip { display: inline-block; font: 500 .74rem/1 var(--mono); color: var(--ink);
  border: 1px solid var(--rule); background: var(--chart); padding: .35rem .55rem; border-radius: 3px; margin: .2rem .3rem .2rem 0; }
.phi-chip b { font-weight: 600; letter-spacing: .04em; }
.muted { color: var(--muted); font-size: .88rem; }
.section-title { font: 600 1.25rem/1.2 var(--display); color: var(--ink); margin: .4rem 0 .6rem; }
.stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--rule); }
.stTabs [data-baseweb="tab"] { font-family: var(--body); font-weight: 500; padding: .55rem .9rem; min-height: 44px; }
[data-testid="stMetricValue"] { font-family: var(--mono); font-variant-numeric: tabular-nums; }
[data-testid="stMetricLabel"] p { font: 500 .72rem/1.3 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.footer { color: var(--muted); font-size: .84rem; text-align: center; margin-top: 2.4rem;
  padding-top: 1rem; border-top: 1px solid var(--rule); }
</style>
""")

# ----------------------------- helpers -----------------------------
def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_note(text):
    html = re.sub(r"\[REDACTED: ([^\]]+)\]", r'<span class="redact" title="Redacted: \1">\1</span>', esc(text))
    st.markdown(f'<div class="note-output">{html}</div>', unsafe_allow_html=True)

def label_week(ws):
    d = date.fromisoformat(ws)
    e = d + timedelta(days=6)
    if d.month == e.month:
        return f"{d.strftime('%b')} {d.day}\u2013{e.day}, {d.year}"
    return f"{d.strftime('%b')} {d.day} \u2013 {e.strftime('%b')} {e.day}, {d.year}"

def resolve_key(sidebar_key):
    if sidebar_key and sidebar_key.strip():
        return sidebar_key.strip(), "your key"
    try:
        sec = st.secrets.get("ANTHROPIC_API_KEY")
        if sec:
            return sec, "configured demo key"
    except Exception:
        pass
    envk = os.environ.get("ANTHROPIC_API_KEY")
    if envk:
        return envk, "local .env key"
    return None, None

def score_bar(label, score, maxv=5):
    pct = int(100 * score / maxv)
    st.markdown(
        f'<div style="margin:.45rem 0;"><div style="display:flex;justify-content:space-between;'
        f'font-size:.9rem;"><span>{label}</span><span style="font-family:var(--mono)"><b>{score:.2f}</b> / {maxv}</span></div>'
        f'<div style="background:var(--rule-soft);border-radius:2px;height:8px;"><div style="width:{pct}%;'
        f'background:var(--accent);height:8px;border-radius:2px;"></div></div></div>',
        unsafe_allow_html=True)

# ----------------------------- header -----------------------------
st.markdown("""
<div class="chart-head">
  <div>
    <p class="kicker">Progress notes · synthetic demo</p>
    <h1>CareScribe</h1>
    <p>Rough shift notes in, objective care documentation out. Every note is screened for protected health information before it is saved.</p>
  </div>
  <div class="spec" role="list" aria-label="Evaluation results">
    <div role="listitem"><b>0.0%</b><span>PHI leakage</span></div>
    <div role="listitem"><b>4.26/5</b><span>Note quality</span></div>
    <div role="listitem"><b>18</b><span>Adversarial cases</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="notice"><b>Prototype</b><span>All data shown is synthetic. Do not enter real patient information. This demo is not a certified HIPAA-compliant system; the About tab lists what production use would require.</span></div>', unsafe_allow_html=True)

# ----------------------------- sidebar -----------------------------
with st.sidebar:
    st.markdown("### CareScribe AI")
    clients = store.list_clients()
    name_to_id = {c["name"]: c["id"] for c in clients}
    names = list(name_to_id.keys())
    sel = st.selectbox("Client", names, index=0,
                       help="Type to search. Each client has their own notes and health record.")
    active_id = name_to_id[sel]
    active = store.get_client(active_id)
    if active.get("profile"):
        st.caption(active["profile"])
    with st.expander("Add a client"):
        nn = st.text_input("Name", key="nc_name")
        npf = st.text_input("Profile (optional)", key="nc_prof")
        if st.button("Add client"):
            if nn.strip():
                store.add_client(nn.strip(), npf.strip())
                st.success(f"Added {nn}")
                st.rerun()
            else:
                st.warning("Enter a name.")
    st.divider()
    sk = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-...",
                       help="Billed to your own account. Never stored. ~1¢ per note.")
    api_key, key_label = resolve_key(sk)
    if api_key:
        st.success(f"Live mode · {key_label}")
    else:
        st.info("Browse mode · history + cached summaries work with no key.")
    st.divider()
    st.caption("Built by Girum Dessalegn · github.com/Girumdess")

def need_key():
    if not api_key:
        st.info("Add your Anthropic API key in the sidebar to run this live.")
        return False
    from care_assistant import config as cfg
    cfg.set_api_key(api_key)
    return True

tab_daily, tab_week, tab_hist, tab_health, tab_eval, tab_about = st.tabs(
    ["Daily note", "Weekly summary", "History", "Health record",
     "Evaluation", "About"])

# ----------------------------- DAILY NOTE -----------------------------
with tab_daily:
    st.markdown(f'<div class="section-title">Daily note — {sel}</div>', unsafe_allow_html=True)
    st.caption("Type or dictate rough notes the way a caregiver would. Do not enter real client data.")
    ndate = st.date_input("Date of service", value=date.today())
    st.caption("Type the rough notes below — voice dictation is planned for the Mac desktop version, where it can run reliably offline.")
    rough = st.text_area("Rough shift notes", key="rough", height=140,
                         placeholder="helped with shower this morning, difficult about lunch, "
                                     "daughter Sarah called at 555-203-4471, gave meds at noon")
    if st.button("Generate compliant note", type="primary"):
        if not rough.strip():
            st.warning("Enter some notes first.")
        elif need_key():
            with st.spinner("Generating and screening for PHI…"):
                from care_assistant import config as cfg
                from care_assistant.pipeline import process_note
                cfg.reset_usage()
                res = process_note(rough, sel.split()[0])
                st.session_state["gen"] = {"res": res, "date": ndate.isoformat(),
                                           "raw": rough, "usage": cfg.get_usage()}
    g = st.session_state.get("gen")
    if g:
        res = g["res"]
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="section-title">Compliant note</div>', unsafe_allow_html=True)
            render_note(res["redacted"])
            with st.expander("Raw draft (before PHI screening)"):
                st.write(res["generated"])
        with c2:
            st.markdown('<div class="section-title">PHI guardrail</div>', unsafe_allow_html=True)
            if res["findings"]:
                for f in res["findings"]:
                    st.markdown(f'<span class="phi-chip"><b>{f["type"]}</b> · {f["source"]}</span>',
                                unsafe_allow_html=True)
                st.caption(f'{len(res["findings"])} identifier(s) redacted.')
            else:
                st.success("No PHI detected.")
            st.caption(f'Cost: ${g["usage"]["cost_usd"]:.4f}')
        if st.button(f"Save to {sel}'s record"):
            store.add_note(active_id, g["date"], g["raw"], res["redacted"])
            st.session_state.pop("gen", None)
            st.success("Saved to the client's record.")
            st.rerun()

# ----------------------------- WEEKLY SUMMARY -----------------------------
with tab_week:
    st.markdown(f'<div class="section-title">Weekly summary — {sel}</div>', unsafe_allow_html=True)
    st.caption("Surfaces only notable or out-of-baseline items — not routine daily care.")
    weeks = store.get_weeks(active_id)
    if not weeks:
        st.info("No notes yet for this client.")
    else:
        wk = st.selectbox("Week", list(weeks.keys()), format_func=label_week)
        notes = weeks[wk]
        with st.expander(f"{len(notes)} daily notes this week"):
            for n in notes:
                st.markdown(f"**{n['note_date']}** — {n['final_note']}")
        skey = f"wsum_{active_id}_{wk}"
        cached = DEMO.get(sel, {}).get("weekly", {}).get(wk)
        summ = st.session_state.get(skey) or cached
        live = bool(st.session_state.get(skey))
        if summ:
            st.markdown(summ)
            st.caption("↻ regenerated live" if live else "cached demo output")
        cta = "Regenerate weekly summary (live)" if summ else "Generate weekly summary"
        if st.button(cta):
            if need_key():
                with st.spinner("Reviewing the week…"):
                    from care_assistant.insights import weekly_summary
                    st.session_state[skey] = weekly_summary(sel, notes)
                    st.rerun()

# ----------------------------- HISTORY -----------------------------
with tab_hist:
    st.markdown(f'<div class="section-title">Note history — {sel}</div>', unsafe_allow_html=True)
    weeks = store.get_weeks(active_id)
    if not weeks:
        st.info("No notes yet for this client.")
    else:
        for ws, notes in weeks.items():
            with st.expander(f"Week of {label_week(ws)}  ·  {len(notes)} notes",
                             expanded=(ws == next(iter(weeks)))):
                for n in notes:
                    st.markdown(f"**{n['note_date']}**")
                    render_note(n["final_note"])

# ----------------------------- HEALTH RECORD -----------------------------
with tab_health:
    st.markdown(f'<div class="section-title">Health overview — {sel}</div>', unsafe_allow_html=True)
    allnotes = store.get_notes(active_id)
    if active.get("profile"):
        st.caption(active["profile"])
    if allnotes:
        st.caption(f"{len(allnotes)} notes · {allnotes[0]['note_date']} to {allnotes[-1]['note_date']}")
    hkey = f"health_{active_id}"
    cached = DEMO.get(sel, {}).get("health")
    rec = st.session_state.get(hkey) or cached
    live = bool(st.session_state.get(hkey))
    if rec:
        st.markdown(rec)
        st.caption("↻ regenerated live" if live else "cached demo output")
    elif not allnotes:
        st.info("No notes yet for this client.")
    cta = "Regenerate health overview (live)" if rec else "Generate health overview"
    if allnotes and st.button(cta):
        if need_key():
            with st.spinner("Reviewing the full record…"):
                from care_assistant.insights import health_record
                st.session_state[hkey] = health_record(sel, allnotes)
                st.rerun()

# ----------------------------- EVALUATION -----------------------------
with tab_eval:
    st.markdown('<div class="section-title">How well does it actually work?</div>', unsafe_allow_html=True)
    if not EVAL:
        st.warning("Evaluation results not found.")
    else:
        s = EVAL["summary"]
        m = st.columns(4)
        m[0].metric("PHI leakage rate", f'{s["phi_leakage_rate_pct"]}%')
        m[1].metric("Documentation quality", f'{s["avg_quality_overall"]} / 5')
        m[2].metric("Test cases", s["n_cases"])
        m[3].metric("Adversarial PHI items", s["phi_items_total"])
        st.caption(f'Run in {s["runtime_sec"]}s · {s["usage"]["calls"]} API calls · '
                   f'est. cost ${s["usage"]["cost_usd"]:.4f}')
        st.divider()
        ok = [r for r in EVAL["results"] if "quality" in r]
        dims = ["objectivity", "completeness", "professional_tone", "no_fabrication"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Average quality by dimension**")
            for d in dims:
                score_bar(d.replace("_", " "), sum(r["quality"][d] for r in ok) / len(ok))
        with c2:
            st.markdown("**Methodology**")
            st.markdown(
                "- **PHI leakage** — each adversarial case plants known identifiers; the metric is "
                "the share that survive the pipeline (target 0%).\n"
                "- **Quality** — an independent LLM judge scores objectivity, completeness, "
                "professional tone, and no-fabrication.\n"
                "- Every input is **synthetic**.")

# ----------------------------- ABOUT -----------------------------
with tab_about:
    st.markdown('<div class="section-title">How it works</div>', unsafe_allow_html=True)
    st.markdown("""
**Daily notes** are drafted by an LLM under a strict documentation policy (objective, person-first,
no judgmental labels, no invented detail), then screened by a **two-layer PHI guardrail**:
deterministic regex for structured identifiers (SSN, phone, email, address, record numbers) plus an
LLM pass for contextual PHI (third-party names, facilities, dates of birth). Anything found is redacted.

**Weekly summaries** review a week of notes and surface only what a supervisor needs — incidents,
changes from baseline, and follow-up items — skipping routine care.

**Health overviews** read a client's full history and extract active concerns, trends over time, and
watch items.

An **evaluation harness** measures PHI-leakage rate and documentation quality on a synthetic test set.
""")
    st.markdown('<div class="section-title">Compliance &amp; privacy</div>', unsafe_allow_html=True)
    st.markdown("""
This is a **prototype demonstrated on synthetic data** — it is **not a certified HIPAA-compliant system**, and the hosted demo should never receive real patient information.

It is built privacy-first: objective, person-first generation plus a two-layer PHI guardrail, validated by a 0%-leakage evaluation. Reaching HIPAA compliance for real-world use would additionally require:
- a signed **Business Associate Agreement (BAA)** with the API provider, on a HIPAA-eligible hosting environment;
- **authentication, role-based access control, and audit logging**;
- **encryption at rest** for stored records, plus encrypted transport;
- organizational safeguards — risk assessments, policies, staff training, and breach-notification procedures.

The PHI guardrail reduces exposure but is a risk-reduction layer, not a substitute for formal Safe-Harbor de-identification.
""")

    st.caption("Generation & insights: Claude Sonnet 4.6 · Detection & scoring: Claude Haiku 4.5 · "
               "All data synthetic.")

st.markdown('<div class="footer">CareScribe AI · prototype · all data synthetic · '
            'built by Girum Dessalegn</div>', unsafe_allow_html=True)
