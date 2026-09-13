"""Deterministic exercise eligibility, relevance, and substitution logic."""

from .models import Exercise, TrainingGoal, UserProfile

LEVELS = {"beginner": 1, "intermediate": 2, "advanced": 3, "elite": 3, "expert": 3}
LIMITATION_RULES = {
    "shoulder": ("shoulder", "overhead", "military press", "upright row", "snatch"),
    "knee": ("squat", "lunge", "leg press", "step-up", "jump", "pistol"),
    "back": ("deadlift", "good morning", "bent over", "barbell row"),
    "wrist": ("push-up", "dip", "curl", "skullcrusher"),
    "hip": ("deadlift", "lunge", "squat", "hip thrust"),
}


def blocked_terms(profile: UserProfile) -> set[str]:
    notes = f"{profile.limitations} {','.join(profile.avoid_exercises)}".lower()
    terms = {item.strip().lower() for item in profile.avoid_exercises if item.strip()}
    for trigger, restricted in LIMITATION_RULES.items():
        if trigger in notes:
            terms.update(restricted)
    return terms


def equipment_available(exercise: Exercise, available: str) -> bool:
    selection = available.lower()
    if any(term in selection for term in ("full gym", "commercial gym", "all equipment")):
        return True
    if exercise.equipment in {"body only", "none", "other"}:
        return True
    aliases = {"dumbbell": "dumbbell", "kettlebells": "kettlebell", "bands": "band"}
    term = aliases.get(exercise.equipment, exercise.equipment)
    return term in selection


def eligible_exercises(exercises: list[Exercise], profile: UserProfile) -> list[Exercise]:
    """Return only exercises compatible with level, equipment, and stated limits."""
    maximum_level = LEVELS.get(profile.experience.lower(), 1)
    blocked = blocked_terms(profile)
    return [
        exercise for exercise in exercises
        if LEVELS.get(exercise.difficulty, 1) <= maximum_level
        and equipment_available(exercise, profile.equipment)
        and not any(term in exercise.name.lower() for term in blocked)
    ]


def score_exercise(exercise: Exercise, target_muscle: str, profile: UserProfile) -> int:
    """Primary-muscle matches decisively outrank secondary-muscle matches."""
    score = 100 if target_muscle in exercise.primary_muscles else 10 if target_muscle in exercise.secondary_muscles else 0
    favorites = " ".join(profile.favorite_exercises).lower()
    if favorites and exercise.name.lower() in favorites:
        score += 25
    if exercise.mechanic == "compound":
        score += 15 if profile.goal == TrainingGoal.STRENGTH else 8
    return score


def ranked_for_target(exercises: list[Exercise], target_muscle: str, profile: UserProfile) -> list[Exercise]:
    return sorted(
        (exercise for exercise in eligible_exercises(exercises, profile) if target_muscle in exercise.primary_muscles),
        key=lambda exercise: (-score_exercise(exercise, target_muscle, profile), exercise.name),
    )


def substitutions(exercise: Exercise, exercises: list[Exercise], profile: UserProfile, limit: int = 3) -> list[Exercise]:
    """Offer same-primary-muscle alternatives with a preference for movement match."""
    candidates = [candidate for candidate in eligible_exercises(exercises, profile) if candidate.name != exercise.name and set(candidate.primary_muscles) & set(exercise.primary_muscles)]
    return sorted(candidates, key=lambda item: (item.movement_pattern != exercise.movement_pattern, item.mechanic != exercise.mechanic, item.name))[:limit]
