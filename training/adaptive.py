"""Persistent, deterministic next-session exercise prescriptions."""

from __future__ import annotations

import re

from training.progression import Recommendation, get_progression_recommendation


def progression_state(connection, member_id, exercise_name):
    """Return one member-owned state row, never a cross-member match."""
    return connection.execute(
        "SELECT * FROM exercise_progression_state WHERE member_id=? AND lower(exercise_name)=lower(?)",
        (member_id, exercise_name),
    ).fetchone()


def progression_states(connection, member_id):
    rows = connection.execute(
        "SELECT * FROM exercise_progression_state WHERE member_id=?", (member_id,)
    ).fetchall()
    return {row["exercise_name"].lower(): dict(row) for row in rows}


def _rep_target(prescription, next_reps):
    if not next_reps:
        return prescription
    # Keep the generated set count and only replace the programmed rep target.
    return re.sub(r"(×\s*)[^·@]+", rf"\g<1>{next_reps} reps", prescription, count=1).replace("reps reps", "reps")


def apply_progression_states(plan, states):
    """Overlay stored recommendations onto freshly generated plan entries."""
    for workout in plan:
        for exercise in workout["exercises"]:
            state = states.get(exercise["name"].lower())
            if not state:
                continue
            exercise["sets_reps"] = _rep_target(exercise["sets_reps"], state.get("recommended_reps"))
            if state.get("recommended_weight") is not None:
                exercise["sets_reps"] = re.sub(r"\s*·\s*Target:\s*[\d.]+\s*lb", "", exercise["sets_reps"], flags=re.I)
                exercise["sets_reps"] += f" · Target: {state['recommended_weight']:g} lb"
            if state.get("recommended_rpe") is not None:
                exercise["sets_reps"] += f" @ RPE {state['recommended_rpe']:g}"
            exercise["progression"] = state
    return plan


def recommendation_for_session(connection, member_id, session_id, exercise_name, sets, prescription, style):
    """Use existing deterministic logic plus this member's prior miss count."""
    prior = progression_state(connection, member_id, exercise_name)
    prior_failures = prior["consecutive_misses"] if prior else 0
    recommendation = get_progression_recommendation(
        sets, prescription, exercise_name, style, prior_failures=prior_failures
    )
    completed = [item for item in sets if item.get("completed") and item.get("actual_reps") is not None]
    rpes = [item.get("actual_rpe") for item in completed if item.get("actual_rpe") is not None]
    # High effort is handled conservatively even when all reps happen to be logged.
    if recommendation.action == "increase" and rpes and max(rpes) >= 9.5:
        recommendation = Recommendation("hold", "Effort was very high. Hold this load and repeat cleanly before increasing.", recommendation.next_weight and max(item.get("actual_weight") or 0 for item in completed), recommendation.next_reps)
    return recommendation


def save_progression_state(connection, member_id, session_id, exercise_name, recommendation, sets):
    """Upsert the latest deterministic outcome for one member/exercise pair."""
    prior = progression_state(connection, member_id, exercise_name)
    misses = (prior["consecutive_misses"] if prior else 0) + 1 if recommendation.action in {"hold", "retry"} else 0
    if recommendation.action in {"increase", "add_reps", "variation", "deload"}:
        misses = 0
    rpes = [item.get("actual_rpe") for item in sets if item.get("actual_rpe") is not None]
    rpe = max(rpes) if rpes else None
    connection.execute(
        """INSERT INTO exercise_progression_state
           (member_id, exercise_name, last_session_id, recommended_weight, recommended_reps,
            recommended_rpe, progression_action, reason, consecutive_misses, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(member_id, exercise_name) DO UPDATE SET
             last_session_id=excluded.last_session_id, recommended_weight=excluded.recommended_weight,
             recommended_reps=excluded.recommended_reps, recommended_rpe=excluded.recommended_rpe,
             progression_action=excluded.progression_action, reason=excluded.reason,
             consecutive_misses=excluded.consecutive_misses, updated_at=CURRENT_TIMESTAMP""",
        (member_id, exercise_name, session_id, recommendation.next_weight, recommendation.next_reps,
         rpe, recommendation.action, recommendation.message, misses),
    )
    return progression_state(connection, member_id, exercise_name)
