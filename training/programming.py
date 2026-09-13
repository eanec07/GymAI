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


def prescription(goal: TrainingGoal, exercise: Exercise, profile: UserProfile) -> tuple[int, int, int]:
    """Return sets, minimum reps, and maximum reps with user preferences applied."""
    if goal == TrainingGoal.STRENGTH:
        defaults = (4 if exercise.mechanic == "compound" else 3, 4 if exercise.mechanic == "compound" else 8, 6 if exercise.mechanic == "compound" else 10)
    elif goal in {TrainingGoal.FAT_LOSS, TrainingGoal.ENDURANCE}:
        defaults = (3, 10, 15 if goal == TrainingGoal.FAT_LOSS else 20)
    else:
        defaults = (3 if exercise.mechanic == "isolation" else 4, 8 if exercise.mechanic == "compound" else 10, 12 if exercise.mechanic == "compound" else 15)
    sets, minimum, maximum = defaults
    preference = profile.preferences
    if preference.preferred_rep_range:
        minimum, maximum = preference.preferred_rep_range
    minimum = preference.min_reps or minimum
    maximum = preference.max_reps or maximum
    return preference.preferred_sets or sets, minimum, maximum


def select_session_exercises(exercises: list[Exercise], targets: tuple[str, ...], profile: UserProfile) -> list[Exercise]:
    """Choose distinct primary-target movements, compounds first, without randomness."""
    limit = 3 if profile.duration_minutes <= 30 else 4 if profile.duration_minutes <= 45 else 5 if profile.duration_minutes <= 60 else 6
    if profile.preferences.max_exercises_per_session:
        limit = min(limit, profile.preferences.max_exercises_per_session)
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
            "exercises": [{
                "name": exercise.name,
                "sets_reps": f"{sets} sets × {minimum}–{maximum} reps",
                "sets": sets,
                "rep_min": minimum,
                "rep_max": maximum,
                "muscles": ", ".join(exercise.primary_muscles),
                "target_muscle": exercise.primary_muscles[0],
                "movement_pattern": exercise.movement_pattern,
                "mechanic": exercise.mechanic,
                "selection_reason": f"Selected for {exercise.primary_muscles[0]} as a {exercise.movement_pattern} movement; it matches your {profile.goal.value} goal, equipment, and experience level.",
            } for exercise in selected for sets, minimum, maximum in [prescription(profile.goal, exercise, profile)]],
            "safety_note": "Your stated limitations were used to remove common aggravating movements. Stop if anything hurts and ask a qualified clinician or coach for individualized guidance." if profile.limitations.strip() else "",
        })
    return program
