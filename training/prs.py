"""Deterministic personal-record comparisons using Epley estimated 1RM."""

from dataclasses import dataclass


def estimated_1rm(weight: float | None, reps: int | None) -> float | None:
    if weight is None or reps is None or weight <= 0 or reps <= 0:
        return None
    return round(weight * (1 + reps / 30), 1)


@dataclass(frozen=True)
class PREvent:
    kind: str
    exercise_name: str
    previous: float | None
    current: float | None
    message: str


def detect_prs(exercise_name: str, current_sets, historical_sets):
    current = [item for item in current_sets if item.get("actual_reps") is not None]
    history = [item for item in historical_sets if item.get("actual_reps") is not None]
    if not current:
        return []
    if not history:
        return [PREvent("baseline", exercise_name, None, None, "Baseline established for this exercise.")]
    events = []
    current_weights = [item.get("actual_weight") or 0 for item in current]
    old_weights = [item.get("actual_weight") or 0 for item in history]
    if max(current_weights) > max(old_weights):
        events.append(PREvent("weight", exercise_name, max(old_weights), max(current_weights), f"New heaviest weight: {max(current_weights):g} lb."))
    for weight in set(current_weights):
        current_best = max(item["actual_reps"] for item in current if (item.get("actual_weight") or 0) == weight)
        old = [item["actual_reps"] for item in history if (item.get("actual_weight") or 0) == weight]
        if old and current_best > max(old):
            events.append(PREvent("reps", exercise_name, max(old), current_best, f"New rep PR: {current_best} reps at {weight:g} lb."))
    current_e1rm = max((estimated_1rm(item.get("actual_weight"), item.get("actual_reps")) or 0 for item in current), default=0)
    old_e1rm = max((estimated_1rm(item.get("actual_weight"), item.get("actual_reps")) or 0 for item in history), default=0)
    if current_e1rm > old_e1rm:
        events.append(PREvent("e1rm", exercise_name, old_e1rm, current_e1rm, f"New estimated 1RM: {old_e1rm:g} → {current_e1rm:g} lb."))
    return events
