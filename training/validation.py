"""Program validation that reports actionable warnings rather than failing silently."""

from .filtering import eligible_exercises
from .models import Exercise, UserProfile


def validate_workout(workout: list[dict], library: list[Exercise], profile: UserProfile) -> list[dict]:
    """Return structured warnings for common programming and preference conflicts."""
    warnings = []
    allowed = {exercise.name for exercise in eligible_exercises(library, profile)}
    by_name = {exercise.name: exercise for exercise in library}
    for session in workout:
        entries = session.get("exercises", [])
        names = [entry["name"] for entry in entries]
        if len(names) != len(set(names)):
            warnings.append({"severity": "warning", "message": f"{session['name']} contains duplicate exercises."})
        max_count = profile.preferences.max_exercises_per_session
        if max_count and len(entries) > max_count:
            warnings.append({"severity": "warning", "message": f"{session['name']} exceeds your maximum exercises per session."})
        seen_isolation = False
        muscle_sets: dict[str, int] = {}
        for entry in entries:
            exercise = by_name.get(entry["name"])
            if entry["name"] not in allowed:
                warnings.append({"severity": "warning", "message": f"{entry['name']} is unavailable, excluded, or above your experience level."})
            if exercise and exercise.mechanic == "isolation":
                seen_isolation = True
            if exercise and exercise.mechanic == "compound" and seen_isolation:
                warnings.append({"severity": "warning", "message": f"{session['name']} places {entry['name']} after an isolation exercise."})
            if not 1 <= entry.get("sets", 0) <= 10 or not 1 <= entry.get("rep_min", 0) <= entry.get("rep_max", 0) <= 50:
                warnings.append({"severity": "warning", "message": f"{entry['name']} has an unreasonable set or rep prescription."})
            for muscle in entry.get("muscles", "").split(", "):
                muscle_sets[muscle] = muscle_sets.get(muscle, 0) + entry.get("sets", 0)
        for muscle, sets in muscle_sets.items():
            if sets >= 10:
                warnings.append({"severity": "warning", "message": f"{session['name']} has high single-session volume for {muscle} ({sets} sets)."})
    return warnings
