"""Deterministic, member-scoped nutrition totals and input validation."""

from datetime import date, datetime

from nutrition import calculate_nutrition

MACROS = ("calories", "protein", "carbs", "fat", "fiber")
LIMITS = {"calories": 20000, "protein": 2000, "carbs": 3000, "fat": 1500, "fiber": 1000}


def nutrition_values(form):
    food_name = form.get("food_name", "").strip()[:160]
    serving = form.get("serving", "").strip()[:160]
    logged_on = datetime.strptime(form.get("logged_on", date.today().isoformat()), "%Y-%m-%d").date().isoformat()
    if not food_name:
        raise ValueError
    values = {name: float(form.get(name, 0) or 0) for name in MACROS}
    if any(value < 0 or value > LIMITS[name] for name, value in values.items()):
        raise ValueError
    return food_name, serving, values, logged_on


def daily_nutrition(connection, member, logged_on=None):
    """Return target, consumed, remaining, and overage for one member/day."""
    logged_on = logged_on or date.today().isoformat()
    targets = calculate_nutrition(member["age"], member["sex"], member["weight"], member["height"], member["goal"], member["days"])
    row = connection.execute(
        "SELECT " + ", ".join(f"COALESCE(SUM({name}), 0) {name}" for name in MACROS) + " FROM nutrition_logs WHERE member_id=? AND logged_on=?",
        (member["id"], logged_on),
    ).fetchone()
    consumed = {name: round(row[name], 1) for name in MACROS}
    remaining = {name: round(max(0, targets[name] - consumed[name]), 1) for name in MACROS}
    over = {name: round(max(0, consumed[name] - targets[name]), 1) for name in MACROS}
    return {"date": logged_on, "targets": targets, "consumed": consumed, "remaining": remaining, "over": over}


def recent_foods(connection, member_id, limit=12):
    return connection.execute(
        """SELECT food_name, serving, calories, protein, carbs, fat, fiber, logged_on
           FROM nutrition_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT ?""",
        (member_id, max(1, min(int(limit), 30))),
    ).fetchall()
