import json
import random
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent / "data" / "exercises.json"
LEVELS = {"beginner": 1, "intermediate": 2, "expert": 3}
SPLITS = {
    1: [("Full Body", ["chest", "lats", "quads", "hamstrings", "shoulders", "abdominals"])],
    2: [("Upper Body", ["chest", "lats", "shoulders", "biceps", "triceps"]), ("Lower Body + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])],
    3: [("Push", ["chest", "shoulders", "triceps"]), ("Pull", ["lats", "middle back", "biceps", "traps"]), ("Legs + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])],
    4: [("Upper Strength", ["chest", "lats", "shoulders", "biceps", "triceps"]), ("Lower Strength", ["quads", "hamstrings", "glutes", "calves"]), ("Upper Hypertrophy", ["chest", "lats", "shoulders", "biceps", "triceps"]), ("Lower + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])],
    5: [("Push", ["chest", "shoulders", "triceps"]), ("Pull", ["lats", "middle back", "biceps", "traps"]), ("Legs", ["quads", "hamstrings", "glutes", "calves"]), ("Upper Body", ["chest", "lats", "shoulders", "biceps", "triceps"]), ("Lower + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])],
    6: [("Push A", ["chest", "shoulders", "triceps"]), ("Pull A", ["lats", "middle back", "biceps", "traps"]), ("Legs A", ["quads", "hamstrings", "glutes", "calves"]), ("Push B", ["chest", "shoulders", "triceps"]), ("Pull B", ["lats", "middle back", "biceps", "traps"]), ("Legs B + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])],
}


def load_exercises():
    with DATA_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def _equipment_matches(exercise_equipment, available_equipment):
    available = available_equipment.lower()
    if any(term in available for term in ("full gym", "commercial gym", "all equipment", "gym")):
        return True
    if exercise_equipment in ("body only", "none", "other"):
        return True
    return exercise_equipment in available


def _prescription(goal, exercise):
    compound = exercise.get("mechanic") == "compound"
    if any(word in goal.lower() for word in ("strength", "power")):
        return "4 sets × 4–6 reps" if compound else "3 sets × 8–10 reps"
    if any(word in goal.lower() for word in ("lose", "fat", "conditioning")):
        return "3 sets × 10–15 reps"
    return "3–4 sets × 8–12 reps" if compound else "3 sets × 10–15 reps"


def _avoid_terms(limitations, avoid_exercises):
    """Turn common limitations into conservative filters, not medical advice."""
    notes = f"{limitations or ''} {avoid_exercises or ''}".lower()
    terms = set()
    rules = {
        ("shoulder", "overhead"): ("shoulder", "overhead", "military press", "upright row", "snatch"),
        ("knee",): ("squat", "lunge", "leg press", "step-up", "jump", "pistol"),
        ("back", "spine", "lower back"): ("deadlift", "good morning", "bent over", "barbell row"),
        ("wrist", "elbow"): ("push-up", "dip", "curl", "skullcrusher"),
        ("hip",): ("deadlift", "lunge", "squat", "hip thrust"),
    }
    for triggers, blocked in rules.items():
        if any(trigger in notes for trigger in triggers):
            terms.update(blocked)
    terms.update(item.strip() for item in (avoid_exercises or "").lower().split(",") if len(item.strip()) > 2)
    return terms


def _candidates(exercises, muscles, equipment, experience, blocked_terms=(), favorite_exercises=""):
    user_level = LEVELS.get("expert" if experience == "advanced" else experience, 1)
    choices = []
    for exercise in exercises:
        if exercise.get("category") != "strength":
            continue
        if LEVELS.get(exercise.get("level", "beginner"), 1) > user_level:
            continue
        if not _equipment_matches((exercise.get("equipment") or "").lower(), equipment):
            continue
        if any(term in exercise["name"].lower() for term in blocked_terms):
            continue
        if set(exercise.get("primaryMuscles", [])).intersection(muscles):
            choices.append(exercise)
    favorites = [item.strip().lower() for item in favorite_exercises.split(",") if item.strip()]
    return sorted(choices, key=lambda exercise: any(term in exercise["name"].lower() for term in favorites), reverse=True)


def generate_workout(equipment, experience, days, goal="muscle gain"):
    """Create a structured, goal-aware weekly plan from the local exercise database."""
    days = max(1, min(int(days), 7))
    split = SPLITS.get(days, SPLITS[6] + [("Active Recovery", ["abdominals"])])
    exercises, plan, used_names = load_exercises(), [], set()
    for index, (name, muscles) in enumerate(split, start=1):
        pool = _candidates(exercises, muscles, equipment, experience)
        fresh_pool = [item for item in pool if item["name"] not in used_names] or pool
        selected = random.sample(fresh_pool, min(6 if "Full" in name else 5, len(fresh_pool)))
        used_names.update(item["name"] for item in selected)
        plan.append({"day": index, "name": name, "focus": ", ".join(muscles).replace("lats", "back"), "exercises": [{"name": item["name"], "sets_reps": _prescription(goal, item), "muscles": ", ".join(item["primaryMuscles"])} for item in selected]})
    return plan


def generate_daily_workout():
    return generate_daily_workout_for_level("beginner")


DAILY_WORKOUTS = {
    "beginner": {
        "subtitle": "Beginner • about 35–45 minutes • focus on controlled, comfortable reps",
        "exercises": [
            ("Bodyweight Squat", "3 sets × 8–12 reps", "legs"),
            ("Push-Up", "3 sets × 6–10 reps", "chest and triceps"),
            ("Dumbbell Row", "3 sets × 8–12 reps each side", "back and biceps"),
            ("Dumbbell Shoulder Press", "2 sets × 8–10 reps", "shoulders"),
            ("Glute Bridge", "3 sets × 10–15 reps", "glutes"),
            ("Plank", "3 sets × 20–30 seconds", "core"),
        ],
    },
    "intermediate": {
        "subtitle": "Intermediate • about 45–55 minutes • leave 1–3 good reps in reserve",
        "exercises": [
            ("Goblet Squat", "3 sets × 8–12 reps", "legs"),
            ("Dumbbell Bench Press", "3 sets × 8–12 reps", "chest and triceps"),
            ("Lat Pulldown", "3 sets × 8–12 reps", "back and biceps"),
            ("Romanian Deadlift", "3 sets × 8–10 reps", "hamstrings and glutes"),
            ("Dumbbell Shoulder Press", "3 sets × 8–12 reps", "shoulders"),
            ("Hanging Knee Raise", "3 sets × 8–12 reps", "core"),
        ],
    },
    "advanced": {
        "subtitle": "Advanced • about 55–70 minutes • use strong form and a challenging load",
        "exercises": [
            ("Barbell Back Squat", "4 sets × 5–8 reps", "legs"),
            ("Barbell Bench Press", "4 sets × 5–8 reps", "chest and triceps"),
            ("Pull-Up", "4 sets × 6–10 reps", "back and biceps"),
            ("Romanian Deadlift", "3 sets × 6–10 reps", "hamstrings and glutes"),
            ("Overhead Press", "3 sets × 6–10 reps", "shoulders"),
            ("Hanging Leg Raise", "3 sets × 10–15 reps", "core"),
        ],
    },
    "elite": {
        "subtitle": "Elite • about 65–80 minutes • only for experienced lifters with reliable technique and recovery",
        "exercises": [
            ("Barbell Back Squat", "5 sets × 3–5 reps", "legs"),
            ("Barbell Bench Press", "5 sets × 3–5 reps", "chest and triceps"),
            ("Weighted Pull-Up", "4 sets × 5–8 reps", "back and biceps"),
            ("Barbell Romanian Deadlift", "4 sets × 6–8 reps", "hamstrings and glutes"),
            ("Barbell Overhead Press", "3 sets × 5–8 reps", "shoulders"),
            ("Ab Wheel Rollout", "3 sets × 8–12 reps", "core"),
        ],
    },
}


def generate_daily_workout_for_level(experience):
    """Return a familiar full-body gym session matched to the visitor's experience."""
    level = experience.lower().strip()
    if level not in DAILY_WORKOUTS:
        level = "beginner"
    workout = DAILY_WORKOUTS[level]
    return {
        "title": "SYLRIX Full-Body Workout of the Day",
        "level": level.title(),
        "subtitle": workout["subtitle"],
        "exercises": [{"name": name, "sets_reps": sets_reps, "muscles": muscles} for name, sets_reps, muscles in workout["exercises"]],
    }


# Every public daily workout follows this weekly rhythm, rather than changing randomly.
WEEKLY_DAILY_TEMPLATES = [
    ("Monday", "Push Strength", [("Push-Up", "Dumbbell Bench Press", "Barbell Bench Press", "Barbell Bench Press"), ("Dumbbell Shoulder Press", "Dumbbell Shoulder Press", "Overhead Press", "Overhead Press"), ("Dumbbell Row", "Seated Cable Row", "Barbell Row", "Weighted Pull-Up"), ("Bodyweight Squat", "Goblet Squat", "Front Squat", "Front Squat"), ("Plank", "Plank", "Ab Wheel Rollout", "Ab Wheel Rollout")]),
    ("Tuesday", "Lower Body", [("Bodyweight Squat", "Goblet Squat", "Barbell Back Squat", "Barbell Back Squat"), ("Glute Bridge", "Romanian Deadlift", "Romanian Deadlift", "Barbell Romanian Deadlift"), ("Reverse Lunge", "Dumbbell Lunge", "Barbell Lunge", "Barbell Lunge"), ("Calf Raise", "Standing Calf Raise", "Standing Calf Raise", "Standing Calf Raise"), ("Dead Bug", "Hanging Knee Raise", "Hanging Leg Raise", "Hanging Leg Raise")]),
    ("Wednesday", "Pull + Core", [("Dumbbell Row", "Lat Pulldown", "Pull-Up", "Weighted Pull-Up"), ("Band Pull-Apart", "Face Pull", "Face Pull", "Face Pull"), ("Dumbbell Curl", "Dumbbell Curl", "Barbell Curl", "Barbell Curl"), ("Glute Bridge", "Hip Thrust", "Barbell Hip Thrust", "Barbell Hip Thrust"), ("Plank", "Hanging Knee Raise", "Hanging Leg Raise", "Ab Wheel Rollout")]),
    ("Thursday", "Conditioning + Mobility", [("Brisk Walk", "Rowing Machine", "Rowing Intervals", "Rowing Intervals"), ("Step-Up", "Kettlebell Swing", "Kettlebell Swing", "Kettlebell Swing"), ("Push-Up", "Push-Up", "Burpee", "Burpee"), ("Bird Dog", "Farmer Carry", "Farmer Carry", "Farmer Carry"), ("Hip Stretch", "Hip Mobility Flow", "Hip Mobility Flow", "Hip Mobility Flow")]),
    ("Friday", "Full-Body Strength", [("Bodyweight Squat", "Goblet Squat", "Barbell Back Squat", "Barbell Back Squat"), ("Push-Up", "Dumbbell Bench Press", "Barbell Bench Press", "Barbell Bench Press"), ("Dumbbell Row", "Lat Pulldown", "Pull-Up", "Weighted Pull-Up"), ("Glute Bridge", "Romanian Deadlift", "Romanian Deadlift", "Barbell Romanian Deadlift"), ("Plank", "Hanging Knee Raise", "Hanging Leg Raise", "Ab Wheel Rollout")]),
    ("Saturday", "Athletic Engine", [("Easy Walk", "Treadmill Incline Walk", "Sled Push", "Sled Push"), ("Bodyweight Squat", "Box Step-Up", "Box Jump", "Box Jump"), ("Push-Up", "Dumbbell Thruster", "Dumbbell Thruster", "Barbell Thruster"), ("Dumbbell Row", "Farmer Carry", "Farmer Carry", "Farmer Carry"), ("Plank", "Suitcase Carry", "Suitcase Carry", "Suitcase Carry")]),
    ("Sunday", "Recovery + Reset", [("Easy Walk", "Easy Walk", "Easy Walk", "Easy Walk"), ("Hip Stretch", "Hip Mobility Flow", "Hip Mobility Flow", "Hip Mobility Flow"), ("Cat-Cow", "Cat-Cow", "Cat-Cow", "Cat-Cow"), ("Bodyweight Glute Bridge", "Glute Bridge", "Glute Bridge", "Glute Bridge"), ("Breathing Reset", "Breathing Reset", "Breathing Reset", "Breathing Reset")]),
]


def weekly_daily_schedule(selected_date):
    start = selected_date - __import__("datetime").timedelta(days=selected_date.weekday())
    return [{"date": start + __import__("datetime").timedelta(days=index), "day": day, "focus": focus} for index, (day, focus, _items) in enumerate(WEEKLY_DAILY_TEMPLATES)]


def generate_daily_workout_for_level(experience, selected_date=None):
    selected_date = selected_date or __import__("datetime").date.today()
    level_index = {"beginner": 0, "intermediate": 1, "advanced": 2, "elite": 3}.get(experience.lower().strip(), 0)
    day, focus, items = WEEKLY_DAILY_TEMPLATES[selected_date.weekday()]
    reps = ("3 sets × 8–12 reps", "3–4 sets × 8–12 reps", "4 sets × 6–10 reps", "4–5 sets × 4–8 reps")[level_index]
    if focus in ("Conditioning + Mobility", "Athletic Engine"):
        reps = ("3 rounds", "4 rounds", "4–5 rounds", "5 rounds")[level_index]
    if focus == "Recovery + Reset":
        reps = "2–3 easy rounds"
    return {"title": f"{day} — {focus}", "level": ("Beginner", "Intermediate", "Advanced", "Elite")[level_index], "subtitle": f"Week-aware SYLRIX daily session • {focus.lower()} • {selected_date.strftime('%B %d')}", "exercises": [{"name": item[level_index], "sets_reps": reps, "muscles": focus.lower()} for item in items]}


def _preferred_split(days, preference):
    preference = preference.lower().strip()
    if preference == "full body":
        return [(f"Full Body {chr(65 + index)}", ["chest", "lats", "quads", "hamstrings", "shoulders", "abdominals"]) for index in range(days)]
    if preference == "upper lower":
        upper = ("Upper Body", ["chest", "lats", "shoulders", "biceps", "triceps"])
        lower = ("Lower Body + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])
        return [upper if index % 2 == 0 else lower for index in range(days)]
    if preference == "push pull legs":
        ppl = [("Push", ["chest", "shoulders", "triceps"]), ("Pull", ["lats", "middle back", "biceps", "traps"]), ("Legs + Core", ["quads", "hamstrings", "glutes", "calves", "abdominals"])]
        return [ppl[index % 3] for index in range(days)]
    return SPLITS.get(days, SPLITS[6] + [("Active Recovery", ["abdominals"])])


def _named_plan(days, title, sessions, goal):
    return [{"day": index + 1, "name": f"{title} — {name}", "focus": focus, "exercises": [{"name": exercise, "sets_reps": prescription, "muscles": focus} for exercise, prescription in exercises]} for index, (name, focus, exercises) in enumerate((sessions * ((days + len(sessions) - 1) // len(sessions)))[:days])]


def generate_workout(equipment, experience, days, goal="muscle gain", training_style="", split_preference="auto", limitations="", session_minutes=60, favorite_exercises="", avoid_exercises=""):
    """Create a plan from schedule, equipment, goals, preferences and safety filters."""
    days = max(1, min(int(days), 7))
    session_minutes = max(20, min(int(session_minutes or 60), 120))
    exercise_limit = 3 if session_minutes <= 30 else 4 if session_minutes <= 45 else 5 if session_minutes <= 60 else 6
    blocked_terms = _avoid_terms(limitations, avoid_exercises)
    style = training_style.lower()
    if "calisthenics" in style or split_preference.lower() == "calisthenics":
        sessions = [("Push", "chest, shoulders, triceps", [("Push-Up", "4 sets × 8–15 reps"), ("Pike Push-Up", "3 sets × 6–12 reps"), ("Bench Dip", "3 sets × 8–15 reps"), ("Hollow Hold", "3 sets × 20–40 seconds")]), ("Pull", "back, biceps, core", [("Assisted Pull-Up", "4 sets × 5–10 reps"), ("Inverted Row", "4 sets × 8–15 reps"), ("Dead Hang", "3 sets × 20–40 seconds"), ("Hanging Knee Raise", "3 sets × 8–15 reps")]), ("Legs", "legs and core", [("Bodyweight Squat", "4 sets × 12–20 reps"), ("Reverse Lunge", "3 sets × 10 reps each side"), ("Glute Bridge", "3 sets × 15 reps"), ("Calf Raise", "3 sets × 15–25 reps")])]
        return _finalize_plan(_named_plan(days, "Calisthenics", sessions, goal), exercise_limit, blocked_terms, limitations)
    if "crossfit" in style or "functional" in style:
        sessions = [("Engine", "conditioning", [("Rowing Intervals", "5 rounds × 250 m"), ("Kettlebell Swing", "5 rounds × 15 reps"), ("Push-Up", "5 rounds × 10 reps"), ("Farmer Carry", "5 rounds × 40 m")]), ("Strength + WOD", "full body", [("Front Squat", "4 sets × 5 reps"), ("Dumbbell Thruster", "4 rounds × 12 reps"), ("Burpee", "4 rounds × 10 reps"), ("Box Step-Up", "4 rounds × 12 reps")])]
        return _finalize_plan(_named_plan(days, "Functional Training", sessions, goal), exercise_limit, blocked_terms, limitations)
    exercises, plan, used_names = load_exercises(), [], set()
    for index, (name, muscles) in enumerate(_preferred_split(days, split_preference), start=1):
        pool = _candidates(exercises, muscles, equipment, experience, blocked_terms, favorite_exercises)
        fresh_pool = [item for item in pool if item["name"] not in used_names] or pool
        selected = random.sample(fresh_pool, min(exercise_limit, len(fresh_pool)))
        used_names.update(item["name"] for item in selected)
        plan.append({"day": index, "name": name, "focus": ", ".join(muscles).replace("lats", "back"), "exercises": [{"name": item["name"], "sets_reps": _prescription(goal, item), "muscles": ", ".join(item["primaryMuscles"])} for item in selected]})
    return _finalize_plan(plan, exercise_limit, blocked_terms, limitations)


def _finalize_plan(plan, exercise_limit, blocked_terms, limitations):
    for session in plan:
        session["exercises"] = [exercise for exercise in session["exercises"] if not any(term in exercise["name"].lower() for term in blocked_terms)][:exercise_limit]
        if not session["exercises"]:
            session["exercises"] = [{"name": "Easy walk + mobility", "sets_reps": "15–20 minutes, easy pace", "muscles": "recovery"}]
        session["safety_note"] = "Your stated limitations were used to remove common aggravating movements. Stop if anything hurts and ask a qualified clinician or coach for individualized guidance." if limitations.strip() else ""
    return plan
