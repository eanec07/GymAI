"""Deterministic next-session recommendations from completed set history."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    action: str
    message: str
    next_weight: float | None = None
    next_reps: str | None = None


def _completed(sets):
    return [item for item in sets if item.get("completed", True) and item.get("actual_reps") is not None]


def strength_progression(sets, target_reps: int, exercise_name: str, prior_failures: int = 0) -> Recommendation:
    completed = _completed(sets)
    if not completed:
        return Recommendation("baseline", "Log a completed session to establish a baseline.")
    weights = [item.get("actual_weight") for item in completed if item.get("actual_weight") is not None]
    successful = len(completed) >= 3 and all(item["actual_reps"] >= target_reps for item in completed[:3])
    weight = max(weights) if weights else None
    if successful and weight is not None:
        lower = any(term in exercise_name.lower() for term in ("squat", "deadlift", "leg press", "lunge"))
        increment = 5 if lower else 2.5
        next_weight = round((weight + increment) * 2) / 2
        return Recommendation("increase", f"Completed all target reps. Next time: {next_weight:g} lb × {target_reps}.", next_weight, str(target_reps))
    if prior_failures >= 2 and weight is not None:
        next_weight = round(weight * .925 / 2.5) * 2.5
        return Recommendation("deload", f"Repeated misses: reduce to {next_weight:g} lb and rebuild with clean reps.", next_weight, str(target_reps))
    return Recommendation("hold", "Keep the same load and complete all target reps before increasing.", weight, str(target_reps))


def hypertrophy_progression(sets, minimum: int, maximum: int) -> Recommendation:
    completed = _completed(sets)
    if not completed:
        return Recommendation("baseline", "Log a completed session to establish a baseline.")
    weights = [item.get("actual_weight") for item in completed if item.get("actual_weight") is not None]
    if weights and len(completed) >= 3 and all(item["actual_reps"] >= maximum for item in completed[:3]):
        next_weight = max(weights) + 5
        return Recommendation("increase", f"You reached {maximum} reps on every set. Increase to {next_weight:g} lb and rebuild from {minimum}–{maximum - 2} reps.", next_weight, f"{minimum}–{maximum - 2}")
    return Recommendation("add_reps", f"Keep the same load and aim to add reps toward {maximum} on each set.", max(weights) if weights else None, f"{minimum}–{maximum}")


def calisthenics_progression(sets, exercise_name: str, successful_sessions: int = 0) -> Recommendation:
    completed = _completed(sets)
    best = max((item["actual_reps"] for item in completed), default=0)
    name = exercise_name.lower()
    if successful_sessions >= 2 and best >= 8 and "assisted pull" in name:
        return Recommendation("variation", "You have repeated strong assisted sets. Reduce assistance or begin controlled negative pull-ups.")
    if successful_sessions >= 2 and best >= 8 and "negative pull" in name:
        return Recommendation("variation", "You have repeated controlled negatives. Test a strict pull-up, then keep building quality reps.")
    if successful_sessions >= 2 and best >= 8 and "pull-up" in name:
        return Recommendation("variation", "Build toward higher-rep bodyweight pull-ups before adding weight.")
    return Recommendation("add_reps", "Keep this variation and add a quality rep when you can maintain control.")


def get_progression_recommendation(sets, prescription: str, exercise_name: str, style: str = "", prior_failures: int = 0) -> Recommendation:
    import re
    targets = [int(value) for value in re.findall(r"\d+", prescription.split("·")[0])]
    rep_values = targets[1:] if len(targets) > 1 else targets
    minimum = min(rep_values, default=5)
    maximum = max(rep_values, default=minimum)
    if "calisthenics" in style.lower() or "pull-up" in exercise_name.lower():
        return calisthenics_progression(sets, exercise_name, prior_failures)
    if maximum - minimum >= 2:
        return hypertrophy_progression(sets, minimum, maximum)
    return strength_progression(sets, minimum, exercise_name, prior_failures)
