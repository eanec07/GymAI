"""Safe, framework-independent workout editing operations."""

from copy import deepcopy

from .filtering import find_substitutes
from .models import Exercise, UserProfile


def replace_exercise(workout: list[dict], old_exercise: str, new_exercise: Exercise) -> list[dict]:
    """Return a copy of a workout with one named exercise replaced."""
    updated = deepcopy(workout)
    for session in updated:
        for item in session["exercises"]:
            if item["name"].lower() == old_exercise.lower():
                item.update({
                    "name": new_exercise.name,
                    "muscles": ", ".join(new_exercise.primary_muscles),
                    "target_muscle": new_exercise.primary_muscles[0],
                    "movement_pattern": new_exercise.movement_pattern,
                    "mechanic": new_exercise.mechanic,
                    "selection_reason": f"Replaced {old_exercise} with an available substitute.",
                })
                return updated
    raise ValueError(f"Exercise not found in workout: {old_exercise}")


def replace_with_best_substitute(workout: list[dict], exercise_name: str, library: list[Exercise], profile: UserProfile) -> tuple[list[dict], dict]:
    """Replace an exercise with the highest-ranked compatible alternative."""
    source = next((item for item in library if item.name.lower() == exercise_name.lower()), None)
    if not source:
        raise ValueError(f"Unknown exercise: {exercise_name}")
    options = find_substitutes(source, library, profile.equipment, profile, limit=1)
    if not options:
        raise ValueError(f"No compatible substitute found for: {exercise_name}")
    return replace_exercise(workout, exercise_name, options[0].exercise), {"exercise": options[0].exercise.name, "score": options[0].score, "reason": options[0].reason}


def change_sets(workout: list[dict], exercise_name: str, sets: int) -> list[dict]:
    if not 1 <= sets <= 10:
        raise ValueError("Sets must be between 1 and 10.")
    updated = deepcopy(workout)
    for session in updated:
        for item in session["exercises"]:
            if item["name"].lower() == exercise_name.lower():
                item["sets"] = sets
                item["sets_reps"] = f"{sets} sets × {item['rep_min']}–{item['rep_max']} reps"
                return updated
    raise ValueError(f"Exercise not found in workout: {exercise_name}")


def change_rep_range(workout: list[dict], exercise_name: str, minimum: int, maximum: int) -> list[dict]:
    if not 1 <= minimum <= maximum <= 50:
        raise ValueError("Rep range must be between 1 and 50 with min <= max.")
    updated = deepcopy(workout)
    for session in updated:
        for item in session["exercises"]:
            if item["name"].lower() == exercise_name.lower():
                item["rep_min"], item["rep_max"] = minimum, maximum
                item["sets_reps"] = f"{item['sets']} sets × {minimum}–{maximum} reps"
                return updated
    raise ValueError(f"Exercise not found in workout: {exercise_name}")
