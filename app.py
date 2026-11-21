"""CareScribe: turns rough caregiver shift notes into objective progress notes,
screens every note for private health information, and builds weekly summaries
and health overviews from a client's record.

All demo data is synthetic.
"""
import html
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from care_assistant import store

st.set_page_config(page_title="CareScribe · care documentation assistant",
                   page_icon=":material/clinical_notes:",
                   layout="wide", initial_sidebar_state="auto")

ROOT = Path(__file__).parent

# Each visitor gets their own seeded copy of the demo records, so nothing one
# visitor adds is ever shown to another.
if "db" not in st.session_state:
    st.session_state["db"] = str(store.new_session_db())
DB = st.session_state["db"]


@st.cache_data
def load_json(rel):
    p = ROOT / rel
    return json.loads(p.read_text()) if p.exists() else None


DEMO = load_json("assets/demo_insights.json") or {}
EVAL = load_json("reports/eval_results.json")
CASES = {r["id"]: r for r in (EVAL or {}).get("results", [])}

# Recorded runs from the evaluation, shown so visitors can see the pipeline
# work without an API key. Text is exactly what the pipeline produced.
EXAMPLES = [
    ("c09", "Hospital follow-up"),
    ("c11", "A family call and a case worker's email"),
    ("c04", "Paperwork with an SSN and home address"),
    ("c05", "Disagreement with another resident"),
    ("c07", "Judgmental wording in the rough notes"),
    ("c06", "A fall during the shift"),
]
EXAMPLES = [(cid, label) for cid, label in EXAMPLES if cid in CASES]

# ----------------------------- styling -----------------------------
st.html("""
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap");
/* Design idea: a care record. Rough notes are typed on ruled slips, filed notes sit
   under an ink rule, and anything private is blacked out like a released record. */
:root {
  --ink: #14213d; --ink-2: #3f4a5c; --muted: #5d6878; --paper: #ffffff; --desk: #f6f4ef;
  --rule: #dcd8ce; --rule-soft: #ebe8e1; --accent: #1e4d8c; --mark: #b4532a; --redact: #111827;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --body: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
html, body, [class*="css"], .stMarkdown, .stTextInput, .stTextArea, button { font-family: var(--body); }
.block-container { padding-top: 3.2rem; max-width: 1140px; }
h1, h2, h3 { font-family: var(--display); letter-spacing: -0.01em; }

/* hero */
.hero { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 2.2rem;
  align-items: center; padding: 1.2rem 0 1.6rem; }
@media (max-width: 860px) { .hero { grid-template-columns: 1fr; gap: 1.4rem; } }
.kicker { font: 500 .72rem/1 var(--mono); letter-spacing: .16em; text-transform: uppercase;
  color: var(--muted); margin: 0 0 .8rem; }
.hero h1 { font: 600 3.1rem/1 var(--display); color: var(--ink); margin: 0; padding: 0; }
.hero .lede { color: var(--ink-2); font-size: 1.12rem; line-height: 1.55; margin: .9rem 0 0; max-width: 46ch; }
.hero .lede b { color: var(--ink); font-weight: 600; }

.specimen { position: relative; }
.slip { background: var(--paper); border: 1px solid var(--rule); border-radius: 3px; padding: .75rem 1rem .6rem;
  font: 400 .86rem/1.6rem var(--mono); color: var(--ink-2); }
.slip .lines { display: block; background-image: linear-gradient(transparent calc(1.6rem - 1px), var(--rule-soft) calc(1.6rem - 1px));
  background-size: 100% 1.6rem; }
.filed { background: var(--paper); border: 1px solid var(--rule); border-top: 3px solid var(--ink);
  border-radius: 0 0 3px 3px; padding: .8rem 1.05rem; font-size: .95rem; line-height: 1.65; color: var(--ink);
  box-shadow: 0 10px 24px -18px rgba(20,33,61,.45); }
.specimen .filed { margin: -.4rem 0 0 1.6rem; position: relative; }
.tag { display: block; font: 500 .64rem/1 var(--mono); letter-spacing: .14em; text-transform: uppercase;
  color: var(--muted); margin-bottom: .45rem; }
.hit { color: var(--mark); text-decoration: underline; text-decoration-thickness: 1.5px; text-underline-offset: 3px; }
.redact { background: var(--redact); color: #fff; padding: .08rem .45rem; border-radius: 2px;
  font: 500 .64rem/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; vertical-align: .1em; white-space: nowrap; }

/* three-step strip */
.steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 2px solid var(--ink);
  border-bottom: 1px solid var(--rule); margin: 0 0 .9rem; }
@media (max-width: 760px) { .steps { grid-template-columns: 1fr; } }
.steps div { padding: .85rem 1rem .9rem 0; }
.steps div + div { padding-left: 1rem; border-left: 1px solid var(--rule); }
@media (max-width: 760px) { .steps div + div { padding-left: 0; border-left: none; border-top: 1px solid var(--rule); } }
.steps .n { font: 500 .7rem/1 var(--mono); color: var(--mark); letter-spacing: .1em; }
.steps b { display: block; font: 600 1.05rem/1.2 var(--display); color: var(--ink); margin: .35rem 0 .25rem; }
.steps span.d { color: var(--ink-2); font-size: .88rem; line-height: 1.45; }

.demo-line { font-size: .84rem; color: var(--muted); margin: 0 0 1.4rem; }
.demo-line b { font: 600 .66rem/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ink);
  border: 1px solid var(--rule); padding: .2rem .4rem; border-radius: 2px; margin-right: .5rem; }

/* content */
.section-title { font: 600 1.3rem/1.2 var(--display); color: var(--ink); margin: .5rem 0 .35rem; }
.note-output { background: var(--paper); border: 1px solid var(--rule); border-top: 2px solid var(--ink);
  border-radius: 0 0 3px 3px; padding: .9rem 1.1rem; line-height: 1.7; font-size: .97rem; color: var(--ink);
  white-space: pre-wrap; margin: .3rem 0; max-width: 75ch; }
.ledger { font: 500 .78rem/1.5 var(--mono); color: var(--ink-2); border-left: 2px solid var(--mark);
  padding: .1rem 0 .1rem .75rem; margin: .9rem 0 .4rem; }
.ledger b { color: var(--ink); }
.phi-chip { display: inline-block; font: 500 .74rem/1 var(--mono); color: var(--ink);
  border: 1px solid var(--rule); background: var(--desk); padding: .35rem .55rem; border-radius: 3px; margin: .2rem .3rem .2rem 0; }
.figures { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--rule);
  border-radius: 3px; background: var(--paper); margin: .6rem 0 1rem; }
@media (max-width: 700px) { .figures { grid-template-columns: 1fr; } }
.figures div { padding: .75rem 1rem; }
.figures div + div { border-left: 1px solid var(--rule); }
.figures b { display: block; font: 500 1.4rem/1.1 var(--mono); color: var(--ink); font-variant-numeric: tabular-nums; }
.figures span { font-size: .82rem; color: var(--muted); }
.stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--rule); }
.stTabs [data-baseweb="tab"] { font-family: var(--body); font-weight: 500; padding: .55rem .9rem; min-height: 44px; }
[data-testid="stSidebar"] .sb-brand { font: 600 1.25rem/1 var(--display); color: var(--ink); margin: .2rem 0 .2rem; }
[data-testid="stSidebar"] .sb-sub { font: 500 .66rem/1.3 var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.footer { color: var(--muted); font-size: .84rem; margin-top: 2.6rem; padding-top: 1rem;
  border-top: 1px solid var(--rule); display: flex; flex-wrap: wrap; justify-content: space-between; gap: .5rem; }
.footer a { color: var(--ink-2); }
</style>
""")


# ----------------------------- helpers -----------------------------
def esc(t):
    return html.escape(t or "", quote=False)


def redaction_html(text):
    return re.sub(r"\[REDACTED: ([^\]]+)\]",
                  lambda m: f'<span class="redact" title="Removed: {m.group(1)}">'
                            f'{m.group(1).replace("_", " ")}</span>',
                  esc(text))


def mark_items(text, items):
    out = esc(text)
    for it in sorted(items, key=len, reverse=True):
        out = out.replace(esc(it), f'<span class="hit">{esc(it)}</span>')
    return out


def render_note(text):
    st.markdown(f'<div class="note-output">{redaction_html(text)}</div>', unsafe_allow_html=True)


def label_week(ws):
    d = date.fromisoformat(ws)
    e = d + timedelta(days=6)
    if d.month == e.month:
        return f"{d.strftime('%b')} {d.day}–{e.day}, {d.year}"
    return f"{d.strftime('%b')} {d.day} – {e.strftime('%b')} {e.day}, {d.year}"


def resolve_key(sidebar_key):
    if sidebar_key and sidebar_key.strip():
        return sidebar_key.strip(), "your key"
    try:
        sec = st.secrets.get("ANTHROPIC_API_KEY")
        if sec:
            return sec, "the demo key"
    except Exception:
        pass
    envk = os.environ.get("ANTHROPIC_API_KEY")
    if envk:
        return envk, "your local .env key"
    return None, None


def score_bar(label, score, maxv=5):
    pct = int(100 * score / maxv)
    st.markdown(
        f'<div style="margin:.5rem 0;"><div style="display:flex;justify-content:space-between;'
        f'font-size:.9rem;color:var(--ink);"><span>{label}</span><span style="font-family:var(--mono)">'
        f'<b>{score:.2f}</b> / {maxv}</span></div>'
        f'<div style="background:var(--rule-soft);border-radius:2px;height:6px;"><div style="width:{pct}%;'
        f'background:var(--accent);height:6px;border-radius:2px;"></div></div></div>',
        unsafe_allow_html=True)


def source_caption(live):
    st.caption("Generated just now from this record." if live
               else "Pre-generated from this record so the demo works without an API key.")


# ----------------------------- hero -----------------------------
hero_case = CASES.get("c09")
if hero_case:
    specimen = (
        '<div class="specimen" aria-label="Example: rough notes and the filed note">'
        f'<div class="slip"><span class="tag">Rough shift notes</span><span class="lines">'
        f'{mark_items(hero_case["input"], hero_case["phi_items"])}</span></div>'
        f'<div class="filed"><span class="tag">Filed progress note</span>'
        f'{redaction_html(hero_case["final"])}</div></div>')
else:
    specimen = ""

st.markdown(f"""
<div class="hero">
  <div>
    <p class="kicker">Care documentation assistant</p>
    <h1>CareScribe</h1>
    <p class="lede">Caregivers type rough shift notes the way they talk. CareScribe turns them into
    <b>objective, professional progress notes</b>, removes private details about anyone in them,
    and builds the weekly summary a supervisor actually needs.</p>
  </div>
  {specimen}
</div>
<div class="steps">
  <div><span class="n">01</span><b>Draft</b><span class="d">An LLM rewrites the rough notes under a documentation policy: objective, person-first, nothing invented.</span></div>
  <div><span class="n">02</span><b>Screen</b><span class="d">Pattern rules and a second model check the draft for names, numbers, addresses and facilities, and black them out.</span></div>
  <div><span class="n">03</span><b>File</b><span class="d">The clean note joins the client's record. Weekly summaries and health overviews are built from that record.</span></div>
</div>
<p class="demo-line"><b>Demo</b>Every client and note here is made up. Please don't enter real client information.</p>
""", unsafe_allow_html=True)

# ----------------------------- sidebar -----------------------------
with st.sidebar:
    st.markdown('<div class="sb-brand">CareScribe</div><div class="sb-sub">Demo records</div>',
                unsafe_allow_html=True)
    clients = store.list_clients(DB)
    name_to_id = {c["name"]: c["id"] for c in clients}
    names = list(name_to_id.keys())
    sel = st.selectbox("Client", names, index=0,
                       help="Each client has their own notes, weekly summaries and health overview.")
    active_id = name_to_id[sel]
    active = store.get_client(active_id, DB)
    if active.get("profile"):
        st.caption(active["profile"])
    with st.expander("Add a client"):
        nn = st.text_input("Name", key="nc_name")
        npf = st.text_input("Profile (optional)", key="nc_prof")
        st.caption("Clients you add stay in your session. Nobody else sees them.")
        if st.button("Add client"):
            if nn.strip():
                store.add_client(nn.strip(), npf.strip(), DB)
                st.success(f"Added {nn.strip()}.")
                st.rerun()
            else:
                st.warning("Enter a name.")
    st.divider()
    with st.expander("Run it live (optional)"):
        sk = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-...",
                           help="Used only for this session and never stored. "
                                "Billed to your own account, about a cent per note.")
    api_key, key_label = resolve_key(sk)
    if api_key:
        st.caption(f"Live: running on {key_label}.")
    else:
        st.caption("Everything here works without a key. A key lets you run your own notes.")
    st.divider()
    st.markdown("Built by Girum Dessalegn  \n"
                "[Source on GitHub](https://github.com/Girumdess/care-note-assistant)")


def use_key():
    from care_assistant import config as cfg
    cfg.set_api_key(api_key)


tab_note, tab_week, tab_hist, tab_health, tab_eval, tab_about = st.tabs(
    ["Write a note", "Weekly summary", "Client history", "Health overview",
     "How it's tested", "About"])

# ----------------------------- WRITE A NOTE -----------------------------
with tab_note:
    modes = ["Recorded examples", "Your own notes"]
    mode = st.segmented_control("Mode", modes, default=modes[1] if api_key else modes[0],
                                label_visibility="collapsed", key="note_mode") or modes[0]

    if mode == modes[0]:
        st.markdown('<div class="section-title">See it work on real pipeline output</div>',
                    unsafe_allow_html=True)
        if not EXAMPLES:
            st.info("Recorded examples aren't available in this copy.")
        else:
            by_label = {label: cid for cid, label in EXAMPLES}
            cid = by_label[st.selectbox("Example", list(by_label))]
            r = CASES[cid]
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown(f'<div class="slip"><span class="tag">Rough notes, as typed</span>'
                            f'<span class="lines">{mark_items(r["input"], r["phi_items"])}</span></div>',
                            unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="filed"><span class="tag">Filed note</span>'
                            f'{redaction_html(r["final"])}</div>', unsafe_allow_html=True)
            planted = r["phi_items"]
            in_draft = [p for p in planted if p in r["generated"]]
            if planted:
                plural = "s" if len(planted) != 1 else ""
                if in_draft:
                    how = (f"The draft still had {len(in_draft)}; the privacy screen removed "
                           f"{'it' if len(in_draft) == 1 else 'them'}.")
                else:
                    how = ("The drafting step already left "
                           f"{'it' if len(planted) == 1 else 'them all'} out, "
                           "and the screen confirmed nothing was left.")
                st.markdown(f'<div class="ledger"><b>{len(planted)}</b> private detail{plural} in '
                            f'the rough notes (underlined) · <b>{len(r["phi_leaked"])}</b> in the '
                            f'filed note. {how}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="ledger">No private details in this one. It shows the '
                            'documentation policy at work: plain, objective wording and nothing '
                            'invented.</div>', unsafe_allow_html=True)
            with st.expander("Compare with the draft before screening"):
                st.write(r["generated"])
            st.caption("Recorded from the evaluation run on June 14, 2026. "
                       "Switch to “Your own notes” to try your own text.")
    else:
        st.markdown(f'<div class="section-title">New note for {esc(sel)}</div>', unsafe_allow_html=True)
        if not api_key:
            st.info("Running your own notes needs an Anthropic API key (about a cent a note). "
                    "Add one under “Run it live” in the sidebar.")
        ndate = st.date_input("Date of service", value=date.today())
        rough = st.text_area("Rough shift notes", key="rough", height=140,
                             placeholder="helped with shower this morning, difficult about lunch, "
                                         "daughter Sarah called at 555-203-4471, gave meds at noon")
        if st.button("Write the note", type="primary", disabled=not api_key):
            if not rough.strip():
                st.warning("Type some rough notes first.")
            else:
                with st.spinner("Drafting and screening…"):
                    use_key()
                    from care_assistant import config as cfg
                    from care_assistant.pipeline import process_note
                    cfg.reset_usage()
                    res = process_note(rough, sel.split()[0])
                    st.session_state["gen"] = {"res": res, "date": ndate.isoformat(), "raw": rough,
                                               "client": active_id, "usage": cfg.get_usage()}
        g = st.session_state.get("gen")
        if g and g.get("client") == active_id:
            res = g["res"]
            c1, c2 = st.columns([3, 2], gap="large")
            with c1:
                st.markdown('<div class="section-title">Filed note</div>', unsafe_allow_html=True)
                render_note(res["redacted"])
                with st.expander("Compare with the draft before screening"):
                    st.write(res["generated"])
            with c2:
                st.markdown('<div class="section-title">Privacy screen</div>', unsafe_allow_html=True)
                if res["findings"]:
                    st.markdown("".join(
                        f'<span class="phi-chip"><b>{esc(f["type"].replace("_", " ").lower())}</b> · '
                        f'{"pattern rule" if f["source"] == "regex" else "model check"}</span>'
                        for f in res["findings"]), unsafe_allow_html=True)
                    n = len(res["findings"])
                    st.caption(f"{n} private detail{'s' if n != 1 else ''} removed.")
                else:
                    st.success("Nothing private found in the draft.")
                st.caption(f'This note cost ${g["usage"]["cost_usd"]:.4f} to write and screen.')
            if st.button(f"Save to {sel}'s record"):
                store.add_note(active_id, g["date"], g["raw"], res["redacted"], DB)
                st.session_state.pop("gen", None)
                st.success("Saved to the record.")
                st.rerun()

# ----------------------------- WEEKLY SUMMARY -----------------------------
with tab_week:
    st.markdown(f'<div class="section-title">Weekly summary for {esc(sel)}</div>', unsafe_allow_html=True)
    st.caption("Only what a supervisor needs: incidents, changes from baseline, and follow-ups. "
               "Routine care is left out.")
    weeks = store.get_weeks(active_id, DB)
    if not weeks:
        st.info("No notes yet for this client.")
    else:
        wk = st.selectbox("Week", list(weeks.keys()), format_func=label_week)
        notes = weeks[wk]
        skey = f"wsum_{active_id}_{wk}"
        cached = DEMO.get(sel, {}).get("weekly", {}).get(wk)
        summ = st.session_state.get(skey) or cached
        live = bool(st.session_state.get(skey))
        if summ:
            with st.container(border=True):
                st.markdown(summ)
            source_caption(live)
        with st.expander(f"The {len(notes)} daily notes behind this summary"):
            for n in notes:
                st.markdown(f"**{n['note_date']}**")
                render_note(n["final_note"])
        cta = "Regenerate live" if summ else "Write this week's summary"
        if st.button(cta, key="week_btn", disabled=not api_key,
                     help=None if api_key else "Needs an API key (sidebar)."):
            use_key()
            with st.spinner("Reading the week…"):
                from care_assistant.insights import weekly_summary
                st.session_state[skey] = weekly_summary(sel, notes)
                st.rerun()

# ----------------------------- HISTORY -----------------------------
with tab_hist:
    st.markdown(f'<div class="section-title">Notes on file for {esc(sel)}</div>', unsafe_allow_html=True)
    weeks = store.get_weeks(active_id, DB)
    if not weeks:
        st.info("No notes yet for this client.")
    else:
        for ws, notes in weeks.items():
            with st.expander(f"Week of {label_week(ws)}  ·  {len(notes)} notes",
                             expanded=(ws == next(iter(weeks)))):
                for n in notes:
                    st.markdown(f"**{n['note_date']}**")
                    render_note(n["final_note"])

# ----------------------------- HEALTH OVERVIEW -----------------------------
with tab_health:
    st.markdown(f'<div class="section-title">Health overview for {esc(sel)}</div>', unsafe_allow_html=True)
    allnotes = store.get_notes(active_id, DB)
    if allnotes:
        st.caption(f"Built from {len(allnotes)} notes, {allnotes[0]['note_date']} to "
                   f"{allnotes[-1]['note_date']}: active concerns, trends over time, and what to watch.")
    hkey = f"health_{active_id}"
    cached = DEMO.get(sel, {}).get("health")
    rec = st.session_state.get(hkey) or cached
    live = bool(st.session_state.get(hkey))
    if rec:
        with st.container(border=True):
            st.markdown(rec)
        source_caption(live)
    elif not allnotes:
        st.info("No notes yet for this client.")
    if allnotes:
        cta = "Regenerate live" if rec else "Write the health overview"
        if st.button(cta, key="health_btn", disabled=not api_key,
                     help=None if api_key else "Needs an API key (sidebar)."):
            use_key()
            with st.spinner("Reading the full record…"):
                from care_assistant.insights import health_record
                st.session_state[hkey] = health_record(sel, allnotes)
                st.rerun()

# ----------------------------- HOW IT'S TESTED -----------------------------
with tab_eval:
    st.markdown("<div class=\"section-title\">How it's tested</div>", unsafe_allow_html=True)
    if not EVAL:
        st.warning("Evaluation results aren't available in this copy.")
    else:
        s = EVAL["summary"]
        ok = [r for r in EVAL["results"] if "quality" in r]
        st.markdown(
            "A privacy screen is only worth something if you've tried to break it. An evaluation "
            f"harness runs **{s['n_cases']} made-up shift notes** through the full pipeline. "
            f"**{s['phi_cases_total']}** of them have private details planted on purpose: phone "
            "numbers, an SSN, a home address, a medical record number, a date of birth, a hospital, "
            "and the names of family, a neighbor, staff and other residents. The rest test everyday "
            "documentation: a fall, a medication refusal, judgmental wording, a vague note.")
        st.markdown(f"""
<div class="figures">
  <div><b>{s['phi_items_leaked']} of {s['phi_items_total']}</b><span>planted details that reached a filed note</span></div>
  <div><b>{s['avg_quality_overall']:.2f} / 5</b><span>average note quality, graded by a separate model</span></div>
  <div><b>{s['n_cases']}</b><span>test notes, all synthetic</span></div>
</div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**Quality by dimension**")
            for d in ["objectivity", "completeness", "professional_tone", "no_fabrication"]:
                score_bar(d.replace("_", " ").capitalize(), sum(r["quality"][d] for r in ok) / len(ok))
        with c2:
            st.markdown("**How the numbers are made**")
            st.markdown(
                "- **Private details:** each planted string is checked against the filed note. "
                "Any that survive count as a leak.\n"
                "- **Quality:** a separate model grades each note from 1 to 5 on objectivity, "
                "completeness, professional tone and not inventing facts.\n"
                "- **Limits:** a small synthetic test set and a single run, and the quality grader "
                "is itself a model. It shows the approach holds up on these cases; it isn't a "
                "clinical validation.")
        st.markdown("**Every test case**")
        rows = [{
            "Case": r["id"],
            "What it tests": r["category"].replace("_", " ").replace(" + ", ", "),
            "Planted details": len(r["phi_items"]),
            "Reached the note": len(r["phi_leaked"]),
            "Quality (1–5)": r["quality"]["overall"],
        } for r in ok]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption(f'Run on {s["timestamp"][:10]} · {s["usage"]["calls"]} model calls · '
                   f'{s["runtime_sec"]}s · about ${s["usage"]["cost_usd"]:.2f}. '
                   "Reproduce it with `python -m evals.run_evals`.")

# ----------------------------- ABOUT -----------------------------
with tab_about:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="section-title">How it works</div>', unsafe_allow_html=True)
        st.markdown("""
**Daily notes.** An LLM drafts the note under a written documentation policy: objective,
person-first, no judgmental labels, no invented detail.

**Privacy screen.** Two layers check every draft. Pattern rules catch structured identifiers
(SSNs, phone numbers, emails, street addresses, record numbers). A second model catches what
patterns can't: names of other people, facilities, dates of birth. Anything found is blacked out
before the note is saved.

**Weekly summaries** read a week of notes and keep only incidents, changes from baseline and
follow-ups. **Health overviews** read the whole record for active concerns, trends and watch items.

Drafting and summaries run on Claude Sonnet 4.6. The privacy check and quality grading run on
Claude Haiku 4.5. Built with Python, Streamlit and SQLite.
""")
    with c2:
        st.markdown('<div class="section-title">Privacy, and what production would need</div>',
                    unsafe_allow_html=True)
        st.markdown("""
This is a **prototype shown on synthetic data**. It is not a certified HIPAA-compliant system,
and the hosted demo should never receive real client information.

Using it with real records would also need:
- a signed **Business Associate Agreement** with the model provider, on HIPAA-eligible hosting;
- **sign-in, role-based access and audit logging**;
- **encryption at rest** for stored records, on top of encrypted transport;
- the organizational side: risk assessments, policies, staff training and breach procedures.

The privacy screen reduces exposure. It is not a substitute for formal Safe Harbor
de-identification.
""")

st.markdown('<div class="footer"><span>CareScribe · prototype on synthetic data</span>'
            '<span>Built by Girum Dessalegn · '
            '<a href="https://github.com/Girumdess/care-note-assistant">source</a></span></div>',
            unsafe_allow_html=True)
