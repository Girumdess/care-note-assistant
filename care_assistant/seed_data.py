"""Synthetic demo data. Entirely fabricated — no real individuals.

Week 1 = Jun 1-7 2026, Week 2 = Jun 8-14 2026. Notes are already in compliant form.
Trends are intentional so weekly summaries and health overviews have signal:
  - Eleanor: a fall (wk1), then cognitive decline + reduced appetite (wk2)
  - Marcus: escalating agitation + medication refusals (wk1), improvement after a schedule change (wk2)
  - Rosa: recurring elevated blood glucose + a heel pressure area that improves
"""
SEED = [
    {
        "name": "Eleanor Hartwell",
        "profile": "Older adult; mobility support with a walker; standby assistance for ADLs.",
        "notes": [
            {"date": "2026-06-02", "final": "Eleanor completed her morning routine with standby assistance. She ate most of her breakfast and lunch and participated in a seated exercise group in the afternoon. Her mood was pleasant throughout the shift."},
            {"date": "2026-06-04", "final": "Eleanor was assisted with morning care. At approximately 2:15 PM she lost her balance while transferring from her chair and lowered to the floor; she did not strike her head. No visible injury was observed and she denied pain. She was assisted up and ambulated without difficulty afterward. The nurse was notified and an incident report was completed."},
            {"date": "2026-06-05", "final": "Eleanor rested more than usual today and declined to attend the afternoon activity. She ate approximately half of each meal. She reported mild soreness in her left hip, and the nurse was informed."},
            {"date": "2026-06-07", "final": "Eleanor participated in morning care with assistance and ate most of her meals. She ambulated in the hallway with her walker without difficulty. No complaints of pain were reported."},
            {"date": "2026-06-09", "final": "Eleanor appeared more confused this morning and required repeated reminders to complete her routine. She asked several times about the day and date. She ate a small breakfast and declined lunch."},
            {"date": "2026-06-11", "final": "Eleanor recognized staff but had difficulty recalling recent events. She ate approximately one quarter of her meals and was encouraged to drink fluids throughout the day. Staff continued to offer preferred foods."},
            {"date": "2026-06-12", "final": "Eleanor declined breakfast and ate a small amount of lunch after encouragement. She spent much of the day resting. Episodes of confusion about her surroundings were observed in the afternoon. The nurse was updated on her reduced intake."},
            {"date": "2026-06-14", "final": "Eleanor accepted assistance with morning care. She ate a small breakfast and remained quiet for much of the shift. Staff continued to monitor her appetite and orientation."},
        ],
    },
    {
        "name": "Marcus Delgado",
        "profile": "Adult receiving behavioral support; independent with most ADLs.",
        "notes": [
            {"date": "2026-06-01", "final": "Marcus completed his morning routine independently. He became frustrated in the afternoon when a planned community outing was delayed, raising his voice and pacing. Staff offered choices and he settled after a short break in his room."},
            {"date": "2026-06-03", "final": "Marcus declined his afternoon medication. Staff offered it again later per protocol and he accepted it at 6:00 PM. He engaged in a preferred activity in the evening without incident."},
            {"date": "2026-06-04", "final": "Marcus was irritable through the morning and declined to participate in group activities. He raised his voice with a peer over use of the television; staff provided redirection and the situation de-escalated. He declined his afternoon medication and the nurse was notified."},
            {"date": "2026-06-06", "final": "Marcus declined both his morning and afternoon medications today. He spent most of the day in his room and engaged minimally with staff. The nurse and program coordinator were notified of the repeated refusals."},
            {"date": "2026-06-08", "final": "Following a review of his schedule, staff introduced a morning walk before activities. Marcus completed the walk and appeared calmer through the morning. He accepted his medications without difficulty."},
            {"date": "2026-06-10", "final": "Marcus participated in the morning walk and engaged in group activities afterward. He accepted all medications as scheduled and interacted positively with peers during lunch."},
            {"date": "2026-06-11", "final": "Marcus completed his routine independently and accepted his medications. He requested and attended a community outing, which he completed without incident. His mood was pleasant throughout."},
            {"date": "2026-06-13", "final": "Marcus participated in all scheduled activities and accepted his medications. He assisted with setting the table at dinner and interacted well with peers and staff."},
        ],
    },
    {
        "name": "Rosa Pittman",
        "profile": "Older adult with diabetes; pre-meal blood glucose monitoring per care plan.",
        "notes": [
            {"date": "2026-06-02", "final": "Rosa completed her morning care with minimal assistance and ate all of her meals. Her blood glucose was checked before meals per her care plan and readings were within her usual range. She enjoyed an afternoon card game."},
            {"date": "2026-06-03", "final": "Rosa's pre-dinner blood glucose reading was higher than her typical range. She reported feeling thirsty. Staff offered water and notified the nurse, who provided guidance. Rosa ate most of her meals."},
            {"date": "2026-06-05", "final": "A small reddened area was observed on Rosa's right heel during evening care. The nurse was notified and the area was documented. Rosa denied pain. She ate all meals and participated in activities."},
            {"date": "2026-06-06", "final": "Rosa's blood glucose readings were elevated before lunch and dinner. She was encouraged to follow her meal plan and stay hydrated. The reddened area on her right heel was unchanged, and the nurse continued to monitor it."},
            {"date": "2026-06-09", "final": "Rosa declined breakfast and ate a small lunch, reporting a reduced appetite. Her blood glucose readings were within range. Staff encouraged fluids and offered preferred foods."},
            {"date": "2026-06-10", "final": "Rosa ate most of her meals today. The reddened area on her right heel appeared improved per the nurse's assessment. She participated in a seated exercise group and was in good spirits."},
            {"date": "2026-06-12", "final": "Rosa's pre-dinner blood glucose was again above her usual range. She reported increased thirst and was offered fluids. The nurse was notified. Rosa ate most of her meals."},
            {"date": "2026-06-14", "final": "Rosa completed her morning routine with minimal assistance. Her blood glucose readings were within range and her right heel continued to appear improved. She ate all meals and enjoyed visiting in the common area."},
        ],
    },
]
