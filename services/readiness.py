"""Deterministic, non-medical daily readiness and session guidance."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ReadinessResult:
    score: int
    classification: str
    explanation: str


def _five_point_score(value):
    return max(0, min(100, (int(value) - 1) * 25))


def _sleep_duration_score(hours):
    hours = float(hours)
    if hours >= 8:
        return 100
    if hours >= 7:
        return 85
    if hours >= 6:
        return 65
    if hours >= 5:
        return 40
    return 15


def calculate_readiness(sleep_hours, sleep_quality, energy, soreness, stress, motivation):
    """Return transparent general-fitness guidance, never medical clearance."""
    score = round(
        _sleep_duration_score(sleep_hours) * .25
        + _five_point_score(sleep_quality) * .15
        + _five_point_score(energy) * .20
        + (100 - _five_point_score(soreness)) * .15
        + (100 - _five_point_score(stress)) * .15
        + _five_point_score(motivation) * .10
    )
    score = max(0, min(100, score))
    classification = "High" if score >= 80 else "Normal" if score >= 60 else "Reduced" if score >= 40 else "Recovery"
    if sleep_hours >= 7 and energy >= 4 and sleep_quality >= 4:
        explanation = "Energy and sleep are strong today."
    elif soreness >= 4 or stress >= 4:
        explanation = "Higher soreness or stress suggests a more measured session."
    elif sleep_hours < 6 or energy <= 2:
        explanation = "Lower sleep or energy suggests keeping today easier."
    else:
        explanation = "Your check-in supports a normal, controlled training day."
    return ReadinessResult(score, classification, explanation)


def readiness_for_today(connection, member_id, logged_on=None):
    logged_on = logged_on or date.today().isoformat()
    row = connection.execute(
        "SELECT * FROM daily_readiness WHERE member_id=? AND logged_on=?", (member_id, logged_on)
    ).fetchone()
    return dict(row) if row else None


def readiness_history(connection, member_id, limit=7):
    return [dict(row) for row in connection.execute(
        "SELECT logged_on, score, classification FROM daily_readiness WHERE member_id=? ORDER BY logged_on DESC LIMIT ?",
        (member_id, limit),
    )]


def training_recommendation(readiness, recent_completed=0, has_progression=False):
    """Choose guidance for one session; it never changes a permanent plan."""
    if not readiness:
        return {"action": "check_in", "label": "Check in first", "message": "A quick readiness check-in will tailor today’s guidance.", "adjustment": "", "load_multiplier": 1.0}
    score = readiness["score"]
    classification = readiness["classification"]
    if classification == "High":
        message = "Train as planned. Your check-in supports a strong training day."
        if has_progression:
            message = "Train as planned and use your saved progression targets if they feel technically solid."
        return {"action": "train_as_planned", "label": "Train as planned", "message": message, "adjustment": "", "load_multiplier": 1.0}
    if classification == "Normal":
        return {"action": "train_as_planned", "label": "Train as planned", "message": "Train as planned, keeping form and effort controlled.", "adjustment": "", "load_multiplier": 1.0}
    if classification == "Reduced":
        action = "reduce_volume" if recent_completed >= 4 else "reduce_load"
        message = "Reduce volume by one working set per exercise today." if action == "reduce_volume" else "Train today, but reduce working weights by approximately 5%."
        return {"action": action, "label": "Reduce volume" if action == "reduce_volume" else "Reduce load", "message": message, "adjustment": action, "load_multiplier": .95}
    if score <= 25:
        return {"action": "rest", "label": "Rest", "message": "A rest day is the conservative choice based on today’s check-in.", "adjustment": "rest", "load_multiplier": 1.0}
    return {"action": "recovery_session", "label": "Recovery session", "message": "Choose an easy recovery-focused session, or rest if that feels better.", "adjustment": "recovery_session", "load_multiplier": 1.0}
