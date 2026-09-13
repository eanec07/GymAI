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


def _candidates(exercises, muscles, equipment, experience):
    user_level = LEVELS.get("expert" if experience == "advanced" else experience, 1)
    choices = []
    for exercise in exercises:
        if exercise.get("category") != "strength":
            continue
        if LEVELS.get(exercise.get("level", "beginner"), 1) > user_level:
            continue
        if not _equipment_matches((exercise.get("equipment") or "").lower(), equipment):
            continue
        if set(exercise.get("primaryMuscles", [])).intersection(muscles):
            choices.append(exercise)
    return choices


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
    """A public, no-account-required workout for the gym's QR code."""
    pool = [item for item in load_exercises() if item.get("category") == "strength" and item.get("level") in ("beginner", "intermediate")]
    selected = random.sample(pool, 6)
    return {"title": "GymAI Full-Body Workout of the Day", "subtitle": "Beginner-friendly • about 45 minutes • choose a comfortable weight", "exercises": [{"name": item["name"], "sets_reps": "3 sets × 8–12 reps", "muscles": ", ".join(item["primaryMuscles"])} for item in selected]}
