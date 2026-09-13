"""Small, predictable weekly workout-program construction functions."""

from .filtering import ranked_for_target
from .models import Exercise, TrainingGoal, UserProfile

SPLITS = {
    "full body": [("Full Body", ("quads", "chest", "lats", "hamstrings", "shoulders", "abdominals"))],
    "upper lower": [("Upper", ("chest", "lats", "shoulders", "biceps", "triceps")), ("Lower + Core", ("quads", "hamstrings", "glutes", "calves", "abdominals"))],
    "push pull legs": [("Push", ("chest", "shoulders", "triceps")), ("Pull", ("lats", "middle back", "biceps")), ("Legs + Core", ("quads", "hamstrings", "glutes", "calves", "abdominals"))],
}


def select_split(profile: UserProfile) -> list[tuple[str, tuple[str, ...]]]:
    preference = profile.split_preference.lower()
    if preference in SPLITS:
        base = SPLITS[preference]
    elif profile.days_per_week <= 2:
        base = SPLITS["full body"]
    elif profile.days_per_week <= 4:
        base = SPLITS["upper lower"]
    else:
        base = SPLITS["push pull legs"]
    return [base[index % len(base)] for index in range(profile.days_per_week)]


def prescription(goal: TrainingGoal, exercise: Exercise) -> str:
    if goal == TrainingGoal.STRENGTH:
        return "4 sets × 4–6 reps" if exercise.mechanic == "compound" else "3 sets × 8–10 reps"
    if goal in {TrainingGoal.FAT_LOSS, TrainingGoal.ENDURANCE}:
        return "3 sets × 10–15 reps"
    return "3–4 sets × 8–12 reps" if exercise.mechanic == "compound" else "3 sets × 10–15 reps"


def select_session_exercises(exercises: list[Exercise], targets: tuple[str, ...], profile: UserProfile) -> list[Exercise]:
    """Choose distinct primary-target movements, compounds first, without randomness."""
    limit = 3 if profile.duration_minutes <= 30 else 4 if profile.duration_minutes <= 45 else 5 if profile.duration_minutes <= 60 else 6
    selected: list[Exercise] = []
    for target in targets:
        candidate = next((item for item in ranked_for_target(exercises, target, profile) if item.name not in {chosen.name for chosen in selected}), None)
        if candidate:
            selected.append(candidate)
        if len(selected) == limit:
            break
    return sorted(selected, key=lambda exercise: (exercise.mechanic != "compound", exercise.name))


def build_weekly_program(exercises: list[Exercise], profile: UserProfile) -> list[dict]:
    """Build a display-ready weekly program using predictable selection rules."""
    program = []
    for day, (name, targets) in enumerate(select_split(profile), start=1):
        selected = select_session_exercises(exercises, targets, profile)
        program.append({
            "day": day,
            "name": name,
            "focus": ", ".join(targets).replace("lats", "back"),
            "exercises": [{"name": exercise.name, "sets_reps": prescription(profile.goal, exercise), "muscles": ", ".join(exercise.primary_muscles)} for exercise in selected],
            "safety_note": "Your stated limitations were used to remove common aggravating movements. Stop if anything hurts and ask a qualified clinician or coach for individualized guidance." if profile.limitations.strip() else "",
        })
    return program
