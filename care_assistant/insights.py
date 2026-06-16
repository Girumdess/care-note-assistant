"""Higher-level insights over a client's notes: weekly summary + health overview."""
from .config import complete, GENERATION_MODEL

WEEKLY_SYSTEM = """You are a clinical supervisor reviewing one week of home-care progress notes for a single individual.
Write a brief WEEKLY SUMMARY that surfaces ONLY what a supervisor needs to know. Do NOT restate routine daily care (normal meals, standard ADLs, ordinary activities).

Include only:
- Notable events or incidents (falls, injuries, medication refusals, behavioral escalations)
- Changes from the individual's baseline (appetite, mood, mobility, cognition, sleep)
- Health concerns or symptoms that may warrant follow-up
- Anything a nurse or care manager should be aware of

Format:
**Notable this week**
- short factual bullets (cite the date)

**Recommend follow-up** (include only if warranted)
- short factual bullets

If the week was entirely routine, respond with a single line saying so. Be concise, objective, and base everything strictly on the notes."""

HEALTH_SYSTEM = """You are a care manager reviewing the full history of home-care notes for a single individual.
Produce a concise HEALTH OVERVIEW using exactly these sections:

**Active concerns**
- current health or behavioral issues evident in the notes

**Trends**
- patterns over time: improving, worsening, or recurring, with rough timeframes / dates

**Watch items**
- specific things staff should continue to monitor

Base everything strictly on the notes. Do not invent diagnoses, vitals, or events. If the evidence is limited, say so plainly. Be concise and factual."""

def _format(notes):
    return "\n".join(f'{n["note_date"]}: {n["final_note"]}' for n in notes)

def weekly_summary(client_name, notes):
    user = f"Individual: {client_name}\n\nDaily notes for the week:\n{_format(notes)}"
    resp = complete(GENERATION_MODEL, max_tokens=700, temperature=0.2,
                    system=WEEKLY_SYSTEM, messages=[{"role": "user", "content": user}])
    return resp.content[0].text.strip()

def health_record(client_name, notes):
    user = f"Individual: {client_name}\n\nAll progress notes (chronological):\n{_format(notes)}"
    resp = complete(GENERATION_MODEL, max_tokens=900, temperature=0.2,
                    system=HEALTH_SYSTEM, messages=[{"role": "user", "content": user}])
    return resp.content[0].text.strip()
