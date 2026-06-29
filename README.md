# CareScribe AI

**Privacy-first care documentation with built-in PHI protection.** CareScribe turns a caregiver's rough shift notes into objective, professional progress notes — and screens every note for protected health information before it is saved.

**▶️ Live demo:** https://care-note-assist.streamlit.app — runs on synthetic demo data, no setup or API key needed.

> ⚠️ Prototype demonstrated entirely on **synthetic data**. Not a certified HIPAA-compliant system. See *Compliance* below.

## What it does
- **Daily notes** — rewrites rough shift notes into objective, person-first, compliant documentation.
- **PHI guardrail** — a two-layer detector (deterministic regex + an LLM contextual pass) finds and redacts SSNs, phone numbers, emails, addresses, record numbers, third-party names, facilities, and dates of birth.
- **Weekly summaries** — surface only notable / out-of-baseline events for a supervisor, skipping routine care.
- **Note history** — every past week, per client.
- **Health overview** — per-client active concerns, trends over time, and watch items.

## Results (synthetic evaluation)
Measured by an automated eval harness over 18 adversarial synthetic cases:
- **0% PHI leakage** — 0 of 14 planted identifiers survived the pipeline.
- **4.26 / 5 documentation quality** — scored by an independent LLM judge on objectivity, completeness, professional tone, and no-fabrication.

## Architecture
Rough notes → **generation** (LLM under a strict documentation policy) → **PHI guardrail** (regex + LLM, with redaction) → compliant note. A SQLite store holds per-client notes; **insights** (weekly summary, health overview) run over a client's history. An **evaluation harness** scores PHI-leakage rate and documentation quality.

- Generation & insights: Claude Sonnet 4.6
- PHI detection & eval scoring: Claude Haiku 4.5

## Tech stack
Python · Streamlit · Anthropic Claude API · SQLite

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env        # then add your Anthropic API key
streamlit run app.py
```
Live generation needs an Anthropic API key (~1¢/note, billed to your own account). The **Examples** and **Evaluation** tabs work with no key.

## Run the evaluation
```bash
PYTHONPATH=. python -m evals.run_evals
```

## Compliance
This is a privacy-by-design prototype on synthetic data — **not** a certified HIPAA-compliant system, and it should never receive real patient information. Production use with real PHI would additionally require a Business Associate Agreement (BAA) with the API provider on HIPAA-eligible hosting, authentication / role-based access control, audit logging, and encryption at rest. The PHI guardrail is a risk-reduction layer, not formal Safe-Harbor de-identification.

## Author
Built by Girum Dessalegn — https://github.com/Girumdess
