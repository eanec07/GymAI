"""Exercise loading and normalization for the local exercise library."""

import json
from functools import lru_cache
from pathlib import Path

from .models import Exercise

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "exercises.json"


def infer_movement_pattern(name: str, primary_muscles: tuple[str, ...]) -> str:
    """Derive a useful Phase 1 movement pattern from the source dataset."""
    text = name.lower()
    if any(word in text for word in ("squat", "lunge", "step-up")):
        return "squat"
    if any(word in text for word in ("deadlift", "good morning", "hyperextension")):
        return "hinge"
    if any(word in text for word in ("bench press", "push-up", "dip", "fly")):
        return "horizontal push"
    if any(word in text for word in ("row", "pulldown", "pull-up", "chin-up")):
        return "horizontal pull" if "row" in text else "vertical pull"
    if any(word in text for word in ("shoulder press", "overhead press", "military press")):
        return "vertical push"
    if "abdominals" in primary_muscles:
        return "core"
    if "calves" in primary_muscles:
        return "calf raise"
    return "isolation"


def load_exercises(path: Path = DATA_FILE) -> list[Exercise]:
    """Load exercises with mtime-aware process caching for request-time use."""
    source_path = Path(path)
    return list(_load_exercises(source_path, source_path.stat().st_mtime_ns))


@lru_cache(maxsize=8)
def _load_exercises(path: Path, _modified_at: int) -> tuple[Exercise, ...]:
    """Parse a dataset once per process, refreshing automatically after edits."""
    with path.open(encoding="utf-8") as source:
        records = json.load(source)
    exercises = []
    for record in records:
        if record.get("category") not in {"strength", "powerlifting"}:
            continue
        primary = tuple(record.get("primaryMuscles") or ())
        if not primary:
            continue
        exercises.append(Exercise(
            name=record["name"],
            primary_muscles=primary,
            secondary_muscles=tuple(record.get("secondaryMuscles") or ()),
            equipment=(record.get("equipment") or "body only").lower(),
            movement_pattern=infer_movement_pattern(record["name"], primary),
            difficulty=record.get("level", "beginner"),
            mechanic=record.get("mechanic") or "isolation",
            category=record["category"],
            instructions=tuple(record.get("instructions") or ()),
            images=tuple(record.get("images") or ()),
        ))
    return tuple(exercises)
