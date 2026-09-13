"""Typed data models used by workout programming."""

from dataclasses import dataclass, field
from enum import Enum


class TrainingGoal(str, Enum):
    STRENGTH = "strength"
    HYPERTROPHY = "muscle gain"
    FAT_LOSS = "fat loss"
    ENDURANCE = "endurance"
    MAINTENANCE = "maintain"

    @classmethod
    def from_text(cls, value: str) -> "TrainingGoal":
        text = (value or "").lower()
        if "strength" in text or "power" in text:
            return cls.STRENGTH
        if "fat" in text or "lose" in text or "cut" in text:
            return cls.FAT_LOSS
        if "endurance" in text or "conditioning" in text:
            return cls.ENDURANCE
        if "maintain" in text or "recomp" in text:
            return cls.MAINTENANCE
        return cls.HYPERTROPHY


@dataclass(frozen=True)
class Exercise:
    name: str
    primary_muscles: tuple[str, ...]
    secondary_muscles: tuple[str, ...]
    equipment: str
    movement_pattern: str
    difficulty: str
    mechanic: str
    category: str


@dataclass(frozen=True)
class TrainingPreferences:
    """Optional programming controls. Empty values use goal-aware defaults."""
    preferred_rep_range: tuple[int, int] | None = None
    preferred_sets: int | None = None
    min_reps: int | None = None
    max_reps: int | None = None
    unavailable_equipment: tuple[str, ...] = field(default_factory=tuple)
    max_exercises_per_session: int | None = None
    automatic_programming: bool = True
    manual_customization: bool = False


@dataclass(frozen=True)
class UserProfile:
    goal: TrainingGoal
    experience: str
    days_per_week: int
    equipment: str
    split_preference: str = "auto"
    limitations: str = ""
    duration_minutes: int = 60
    favorite_exercises: tuple[str, ...] = field(default_factory=tuple)
    avoid_exercises: tuple[str, ...] = field(default_factory=tuple)
    preferences: TrainingPreferences = field(default_factory=TrainingPreferences)
