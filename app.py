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
    from streamlit_mic_recorder import speech_to_text
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
st.markdown("""
<style>
.block-container { padding-top: 2rem; max-width: 1150px; }
.hero { background: linear-gradient(120deg,#0E7C7B 0%,#115E59 100%);
        padding: 1.8rem 2rem; border-radius: 16px; margin-bottom: 1.3rem; }
.hero h1 { color:#fff; font-size:1.95rem; margin:0 0 .3rem 0; font-weight:750; letter-spacing:-.5px;}
.hero p { color:#D7EEEC; font-size:1.02rem; margin:0; }
.hero .badge { display:inline-block; background:rgba(255,255,255,.16); color:#fff;
        padding:.28rem .7rem; border-radius:999px; font-size:.8rem; margin:.85rem .5rem 0 0;}
.note-output { background:#F7FBFB; border-left:4px solid #0E7C7B; border-radius:8px;
        padding:.9rem 1.1rem; line-height:1.6; font-size:.96rem; white-space:pre-wrap; margin:.3rem 0;}
.redact { background:#FEE2E2; color:#991B1B; padding:0 .25rem; border-radius:3px; font-weight:650; }
.phi-chip { display:inline-block; background:#FEF2F2; color:#B91C1C; border:1px solid #FCA5A5;
        padding:.26rem .6rem; border-radius:8px; font-size:.8rem; margin:.2rem .3rem .2rem 0; }
.muted { color:#5C6B69; font-size:.88rem; }
.section-title { font-size:1.08rem; font-weight:700; color:#16302B; margin:.3rem 0 .5rem; }
.footer { color:#8A9997; font-size:.84rem; text-align:center; margin-top:2.4rem;
        padding-top:1rem; border-top:1px solid #E2EAEA; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- helpers -----------------------------
def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_note(text):
    html = re.sub(r"\[REDACTED: ([^\]]+)\]", r'<span class="redact">[\1 ✕]</span>', esc(text))
    st.markdown(f'<div class="note-output">{html}</div>', unsafe_allow_html=True)

def label_week(ws):
    d = date.fromisoformat(ws); e = d + timedelta(days=6)
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
        f'font-size:.9rem;"><span>{label}</span><span><b>{score:.2f}</b> / {maxv}</span></div>'
        f'<div style="background:#E2EAEA;border-radius:6px;height:9px;"><div style="width:{pct}%;'
        f'background:#0E7C7B;height:9px;border-radius:6px;"></div></div></div>',
        unsafe_allow_html=True)

# ----------------------------- header -----------------------------
st.markdown("""
<div class="hero">
  <h1>🩺 CareScribe&nbsp;AI</h1>
  <p>Compliant care documentation with PHI protection — daily notes, weekly highlights, and client health trends.</p>
  <div>
    <span class="badge">✓ 0.0% PHI leakage on the test set</span>
    <span class="badge">✓ 4.26 / 5 documentation quality</span>
    <span class="badge">✓ All demo data synthetic</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="background:#FFF7ED;border:1px solid #FED7AA;color:#9A3412;padding:.6rem .9rem;border-radius:8px;font-size:.85rem;margin-bottom:1rem;">⚠️ <b>Prototype.</b> All data shown is synthetic. Do not enter real patient information. This demo is not a certified HIPAA-compliant system — see the <b>About</b> tab for what production compliance requires.</div>', unsafe_allow_html=True)

# ----------------------------- sidebar -----------------------------
with st.sidebar:
    st.markdown("### CareScribe AI")
    clients = store.list_clients()
    name_to_id = {c["name"]: c["id"] for c in clients}
    names = list(name_to_id.keys())
    sel = st.selectbox("👤 Client", names, index=0,
                       help="Type to search. Each client has their own notes and health record.")
    active_id = name_to_id[sel]
    active = store.get_client(active_id)
    if active.get("profile"):
        st.caption(active["profile"])
    with st.expander("➕ Add a client"):
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
    ["✍️ Daily Note", "📅 Weekly Summary", "📚 History", "🩺 Health Record",
     "📊 Evaluation", "ⓘ About"])

# ----------------------------- DAILY NOTE -----------------------------
with tab_daily:
    st.markdown(f'<div class="section-title">Daily note — {sel}</div>', unsafe_allow_html=True)
    st.caption("Type or dictate rough notes the way a caregiver would. Do not enter real client data.")
    ndate = st.date_input("Date of service", value=date.today())
    st.caption("Type the rough notes below — voice dictation is planned for the Mac desktop version, where it can run reliably offline.")
    rough = st.text_area("Rough shift notes", key="rough", height=140,
                         placeholder="helped John shower, difficult about lunch, "
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
        if st.button(f"💾 Save to {sel}'s record"):
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
