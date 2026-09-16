"""SYLRIX Coach providers plus narrowly scoped, member-safe data tools."""
import json
import os
import re
import sqlite3
from datetime import date
from contextlib import closing

from nutrition import calculate_nutrition
from services.nutrition_tracking import daily_nutrition, recent_foods
from training.exercise_repository import load_exercises
from training.filtering import find_substitutes
from training.models import TrainingGoal, UserProfile
from training.progression import get_progression_recommendation
from training.adaptive import apply_progression_states, progression_states
from workouts import generate_workout
from services.coach_prompt import SYSTEM_INSTRUCTIONS
from services.coach_tools import CoachToolRegistry, TOOL_DEFINITIONS as REGISTRY_TOOL_DEFINITIONS, ALLOWED_TOOL_NAMES as REGISTRY_ALLOWED_TOOL_NAMES

MODEL = os.environ.get("SYLRIX_AI_MODEL", "gpt-5.6-terra")
COACH_MODE = os.environ.get("SYLRIX_COACH_MODE", "local").lower()

def _tool_definition(name, description, properties=None):
    return {"type": "function", "name": name, "description": description, "parameters": {"type": "object", "properties": properties or {}, "additionalProperties": False}, "strict": True}


_EXERCISE_ARGUMENTS = {"exercise_name": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 30}}
TOOL_DEFINITIONS = [
    _tool_definition("get_member_profile", "Safe profile for the signed-in athlete."),
    _tool_definition("get_member_goals", "Goals, goal weight, and training objective for the signed-in athlete."),
    _tool_definition("get_training_preferences", "Training preferences for the signed-in athlete."),
    _tool_definition("get_today_workout", "Currently active workout for the signed-in athlete."),
    _tool_definition("get_recent_workouts", "Recent completed sessions.", {"limit": _EXERCISE_ARGUMENTS["limit"]}),
    _tool_definition("get_workout_history", "Completed sessions and their sets.", {"limit": _EXERCISE_ARGUMENTS["limit"]}),
    _tool_definition("get_recent_exercises", "Recently performed exercises.", {"limit": _EXERCISE_ARGUMENTS["limit"]}),
    _tool_definition("get_exercise_performance", "Logged performance for one exercise.", _EXERCISE_ARGUMENTS),
    _tool_definition("get_progression", "Deterministic next-session recommendation.", _EXERCISE_ARGUMENTS),
    _tool_definition("get_personal_records", "Recorded PRs, optionally for one exercise.", _EXERCISE_ARGUMENTS),
    _tool_definition("get_weight_progress", "Latest, starting, change, goal distance, and trend."),
    _tool_definition("get_recent_weight_logs", "Recent body-weight entries.", {"limit": _EXERCISE_ARGUMENTS["limit"]}),
    _tool_definition("get_nutrition_summary", "Nutrition targets and recent logged nutrition."),
    _tool_definition("get_recent_nutrition", "Bounded recent nutrition totals."),
    _tool_definition("get_steps", "Today's and recent step totals."),
    _tool_definition("get_progress_summary", "Compact recent athlete progress summary."),
    _tool_definition("get_exercise_information", "Trusted metadata and instructions for a local exercise.", _EXERCISE_ARGUMENTS),
    _tool_definition("search_exercises", "Search local exercises by name, muscle, or equipment.", {"query": {"type": "string"}, "muscle": {"type": "string"}, "equipment": {"type": "string"}, "limit": _EXERCISE_ARGUMENTS["limit"]}),
    _tool_definition("find_exercise_substitutes", "Equipment-aware local substitutes.", _EXERCISE_ARGUMENTS),
]
ALLOWED_TOOL_NAMES = {tool["name"] for tool in TOOL_DEFINITIONS}
MAX_TOOL_ITERATIONS = 4
# The registry owns the provider contract; this compatibility alias preserves
# imports used by existing integrations while moving schemas out of this service.
TOOL_DEFINITIONS = REGISTRY_TOOL_DEFINITIONS
ALLOWED_TOOL_NAMES = REGISTRY_ALLOWED_TOOL_NAMES


class CoachService:
    def __init__(self, database_path, member_id=None):
        self.database_path = database_path
        self.member_id = member_id
        self.last_error = None
        self.tools = CoachToolRegistry(member_id, self._tool) if member_id is not None else None

    @property
    def configured(self):
        """Whether paid OpenAI responses have deliberately been enabled."""
        return COACH_MODE == "openai" and bool(os.environ.get("OPENAI_API_KEY"))

    @property
    def local_mode(self):
        """The free deterministic Coach is always available to signed-in members."""
        return not self.configured

    def _connection(self):
        db = sqlite3.connect(self.database_path)
        db.row_factory = sqlite3.Row
        return db

    def _member(self, db, member_id):
        return db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()

    def _profile(self, db, member_id):
        member = self._member(db, member_id)
        if not member:
            return {}
        preferences = {row["preference_key"]: row["preference_value"] for row in db.execute("SELECT preference_key, preference_value FROM training_preferences WHERE member_id=?", (member_id,))}
        fields = ("goal", "training_style", "experience", "days", "session_minutes", "equipment", "equipment_notes", "limitations", "favorite_exercises", "avoid_exercises")
        return {**{field: member[field] for field in fields}, "training_preferences": preferences}

    def _exercise(self, value):
        needle = (value or "").lower()
        return next((item for item in load_exercises() if needle in item.name.lower()), None)

    def _exercise_in_message(self, message):
        """Find the most specific trusted-library exercise mentioned in a question."""
        lowered = (message or "").lower().replace("-", " ")
        matches = [item for item in load_exercises() if item.name.lower() in lowered]
        aliases = {
            "bench": "Bench Press - Powerlifting", "pull up": "Pull-Up", "pullups": "Pull-Up",
            "deadlift": "Deadlift", "bulgarian split squat": "Bulgarian Split Squat",
        }
        if not matches:
            for phrase, name in aliases.items():
                if phrase in lowered:
                    matches = [item for item in load_exercises() if item.name.lower() == name.lower()]
                    break
        return max(matches, key=lambda item: len(item.name), default=None)

    @staticmethod
    def _plan_exercise(exercise):
        prescription = exercise.get("sets_reps", "")
        weight = re.search(r"Target:\s*([\d.]+)\s*lb", prescription, re.I)
        rpe = re.search(r"RPE\s*([\d.]+)", prescription, re.I)
        return {
            "name": exercise["name"],
            "sets_reps": prescription,
            "target_weight": float(weight.group(1)) if weight else None,
            "target_rpe": float(rpe.group(1)) if rpe else None,
            "muscles": exercise.get("muscles", ""),
        }

    def _training_plan(self, db, member):
        preferences = {
            row["preference_key"]: row["preference_value"]
            for row in db.execute("SELECT preference_key, preference_value FROM training_preferences WHERE member_id=?", (member["id"],))
        }
        plan = generate_workout(
            f'{member["equipment"]} {member["equipment_notes"]}', member["experience"], member["days"],
            f'{member["goal"]} {member["custom_goal"]}', member["training_style"], member["split_preference"],
            member["limitations"], member["session_minutes"], member["favorite_exercises"],
            member["avoid_exercises"], preferences,
        )
        plan = apply_progression_states(plan, progression_states(db, member["id"]))
        return [
            {"day": day["day"], "name": day["name"], "focus": day.get("focus", ""),
             "exercises": [self._plan_exercise(exercise) for exercise in day["exercises"]]}
            for day in plan
        ]

    @staticmethod
    def _format_number(value):
        return f"{float(value):g}"

    def local_reply(self, member_id, message):
        """Free rule-based coaching that never sends a request to an AI provider."""
        question = (message or "").strip()
        lowered = question.lower()
        exercise = self._exercise_in_message(question)

        # Safety comes before an ordinary training recommendation.
        urgent_words = ("chest pain", "trouble breathing", "can't breathe", "numb", "tingling", "sudden weakness", "major swelling")
        if any(word in lowered for word in urgent_words):
            return "Stop training and seek urgent medical care now. Those symptoms need an in-person professional assessment."
        if any(word in lowered for word in ("hurt", "pain", "injury", "injured")):
            return "I can give general training guidance, but I cannot diagnose an injury. Stop any movement that causes sharp or worsening pain. Consider a qualified clinician or physical therapist, especially if it persists, limits normal movement, or follows a sudden injury."

        if any(word in lowered for word in ("latest weight", "weight changed", "weight have i", "starting weight", "weigh-in", "weigh in", "weight goal", "from my goal")):
            progress = self._tool(member_id, "get_weight_progress", {})
            if not progress.get("entries"):
                return "SYLRIX does not have body-weight entries yet. Log a weigh-in in Progress and I can track the trend."
            answer = f"Your latest logged weight is {progress['latest_weight']:g} lb on {progress['latest_date']}. Since {progress['starting_date']}, that is {progress['change']:+g} lb."
            if progress.get("goal_weight") is not None:
                answer += f" Your goal is {progress['goal_weight']:g} lb; you are {abs(progress['distance_from_goal']):g} lb {'above' if progress['distance_from_goal'] < 0 else 'below'} it."
            return answer

        if any(word in lowered for word in ("dumbbell", "hamstring exercise", "chest exercise", "what exercises")) and not exercise:
            results = self._tool(member_id, "search_exercises", {"query": "", "muscle": "chest" if "chest" in lowered else "hamstrings" if "hamstring" in lowered else "", "equipment": "dumbbell" if "dumbbell" in lowered else "", "limit": 5})
            items = results.get("exercises", [])
            if items:
                return "From the SYLRIX library: " + "; ".join(f"{item['name']} ({item['equipment']})" for item in items) + "."

        if re.search(r"\bpr\b", lowered) or "personal record" in lowered or "personal best" in lowered:
            exercise_query = exercise.name if exercise else next((term for term in ("bench", "squat", "deadlift") if term in lowered), "")
            records = self._tool(member_id, "get_pr_history", {"exercise_name": exercise_query, "limit": 5})
            if not records["records"]:
                return records["message"]
            if exercise or exercise_query:
                best = records["best_by_type"]
                details = []
                if "weight" in best:
                    details.append(f"heaviest weight {best['weight']['value']:g} lb")
                if "e1rm" in best:
                    details.append(f"estimated 1RM {best['e1rm']['value']:g} lb")
                return f"Your recorded {(exercise.name if exercise else exercise_query)} PRs: " + ", ".join(details or ["baseline established"]) + "."
            return "Recent PRs: " + "; ".join(f"{item['exercise_name']} — {item['pr_type']} ({item['achieved_at']})" for item in records["records"]) + "."

        if any(word in lowered for word in ("this week", "my plan", "supposed to train", "weekly plan", "training plan")):
            plan = self._tool(member_id, "get_training_plan", {})
            return "Your current weekly plan: " + "; ".join(f"Day {day['day']}: {day['name']}" for day in plan) + "."

        if any(word in lowered for word in ("weekly recap", "how am i doing", "making progress", "getting stronger", "progress summary", "what should i focus")):
            summary = self._tool(member_id, "get_progress_summary", {})
            parts = [f"{summary['completed_workouts']} completed workout(s)", f"{summary['training_volume']:g} lb of tracked volume"]
            if summary["recent_prs"]:
                parts.append(f"{len(summary['recent_prs'])} recent PR event(s)")
            if summary["steps"].get("days_logged"):
                parts.append(f"{summary['steps'].get('average_steps', 0):,} average daily steps")
            return "Your last 7 days: " + ", ".join(parts) + "."

        if any(word in lowered for word in ("protein", "calorie", "calories", "macros", "eat")):
            if any(word in lowered for word in ("week", "consistent", "been hitting", "history")):
                history = self._tool(member_id, "get_nutrition_history", {})
                if not history["daily"]:
                    return history["message"]
                average = history["averages"]
                return f"In your last 7 days, you logged nutrition on {history['days_logged']} day(s). Your average logged protein was {average['protein']:g} g and average calories were {average['calories']:g}."
            data = self._tool(member_id, "get_today_nutrition", {})
            targets, logged, remaining = data["targets"], data["consumed"], data["remaining"]
            if "protein" in lowered:
                return f"Your current SYLRIX protein target is {targets['protein']} g. You have logged {self._format_number(logged['protein'])} g today, with {self._format_number(remaining['protein'])} g remaining."
            return f"Your target is about {targets['calories']} calories and {targets['protein']} g protein for {targets['goal_type'].lower()}. You have logged {self._format_number(logged['calories'])} calories, with {self._format_number(remaining['calories'])} calories remaining."

        if "step" in lowered:
            steps = self._tool(member_id, "get_steps", {})
            if isinstance(steps, dict):
                return "SYLRIX does not have step data logged yet. Add today’s steps on the Steps page and I can use them here."
            today = steps[0] if steps else None
            return f"Your most recent step entry is {today['steps']:,} steps against a {today['goal']:,}-step goal on {today['logged_on']}." if today else "SYLRIX does not have step data logged yet."

        if any(word in lowered for word in ("today", "current workout", "training today")):
            current = self._tool(member_id, "get_today_workout", {})
            if "message" in current:
                return "You do not have an active workout yet. Open your plan and choose Start Workout for the day you want to train."
            names = []
            for entry in current["sets"]:
                if entry["exercise_name"] not in names:
                    names.append(entry["exercise_name"])
            return f"Your active workout is {current['session']['workout_name']}: " + ", ".join(names) + "."

        if any(word in lowered for word in ("last time", "last workout", "how did i do", "history", "recent progress")):
            if exercise:
                records = self._tool(member_id, "get_exercise_history", {"exercise_name": exercise.name, "limit": 3})
                if isinstance(records, dict):
                    return f"SYLRIX does not have any completed {exercise.name} sets logged yet. Complete and save a workout first."
                latest = records[0]
                weight = latest["actual_weight"]
                detail = f"{self._format_number(weight)} lb × {latest['actual_reps']}" if weight is not None else f"{latest['actual_reps']} reps"
                return f"Your latest logged {exercise.name} set was {detail} on {latest['completed_at']}."
            workouts = self._tool(member_id, "get_recent_workouts", {"limit": 3})
            if not workouts:
                return "SYLRIX does not have a completed workout saved yet. Finish an active workout to begin building your history."
            return "Your recent completed workouts: " + "; ".join(f"{item['workout_name']} ({item['completed_at']})" for item in workouts) + "."

        if any(word in lowered for word in ("increase", "progress", "weight should", "what weight")) and exercise:
            saved = self._tool(member_id, "get_exercise_progression", {"exercise_name": exercise.name})
            if "recommended_weight" in saved:
                target = f"{saved['recommended_weight']:g} lb" if saved["recommended_weight"] is not None else "your current bodyweight/load"
                reps = f" for {saved['recommended_reps']} reps" if saved.get("recommended_reps") else ""
                return f"Your saved next target for {saved['exercise_name']} is {target}{reps}. {saved['reason']}"
            result = self._tool(member_id, "get_progression", {"exercise_name": exercise.name})
            return result.get("recommendation", result.get("message", "Log a completed workout first so SYLRIX can calculate a recommendation."))

        if any(word in lowered for word in ("replace", "substitute", "swap")) and exercise:
            choices = self._tool(member_id, "find_exercise_substitutes", {"exercise_name": exercise.name, "limit": 3})
            if isinstance(choices, dict):
                return choices["message"]
            if not choices:
                return f"I could not find a suitable local substitute for {exercise.name} with your current equipment and preferences."
            options = "; ".join(f"{item['exercise']} — {item['reason']}" for item in choices[:3])
            return f"Possible replacements for {exercise.name}: {options}. Use Replace Exercise during an active workout to apply one."

        if exercise and any(word in lowered for word in ("muscle", "work", "what is", "explain")):
            data = self._tool(member_id, "find_exercise", {"exercise_name": exercise.name})
            return f"{data['name']} primarily trains {', '.join(data['primary_muscles'])}. It also involves {', '.join(data['secondary_muscles']) or 'few secondary muscles'}. It is a {data['movement_pattern']} movement using {data['equipment']}."

        if "rpe" in lowered:
            return "RPE is rate of perceived exertion. RPE 7 usually means you could have completed about 3 more good reps; RPE 8 means about 2 more. Use it to keep effort productive without grinding every set."
        if "rest" in lowered:
            return "For heavy compound lifts, rest about 2–4 minutes. For most muscle-building accessory work, 60–120 seconds is a solid starting point. Rest longer if form or performance drops."
        if "pull" in lowered:
            return "To improve pull-ups, train a progression you can control: assisted pull-ups or negatives, plus rows and pulldowns if available. Accumulate quality reps 2–3 times each week and gradually reduce assistance."
        if "bench" in lowered:
            return "For a stronger bench, practice it consistently, keep your upper back tight, use a controlled touch point, and add small amounts of weight or reps only when your current sets are solid."

        return "I am currently in free local Coach mode. I can help with your plan, workout history, exercise substitutions, nutrition targets, steps, RPE, rest times, pull-ups, and common training questions. Try: “What muscles does bench press work?”"

    def _tool(self, member_id, name, arguments=None):
        arguments = arguments or {}
        # The model may never choose a member ID; this server-only argument is the
        # authenticated member identity supplied by the Flask route.
        aliases = {"get_exercise_performance": "get_exercise_history", "get_personal_records": "get_pr_history", "get_nutrition_summary": "get_today_nutrition", "get_recent_nutrition": "get_nutrition_history", "get_exercise_information": "find_exercise", "get_exercise_progression": "get_saved_progression", "get_recent_prs": "get_pr_history", "get_training_progress_summary": "get_progress_summary"}
        if name not in ALLOWED_TOOL_NAMES and name not in {"get_training_plan", "get_exercise_history", "get_pr_history", "get_nutrition_targets", "get_nutrition_history", "find_exercise"}:
            return {"message": "That tool is unavailable."}
        name = aliases.get(name, name)
        with closing(self._connection()) as db:
            member = self._member(db, member_id)
            if not member:
                return {}
            limit = max(1, min(int(arguments.get("limit", 10) or 10), 30))
            if name == "get_member_profile":
                return self._profile(db, member_id)
            if name == "get_member_goals":
                return {"goal": member["goal"], "custom_goal": member["custom_goal"], "goal_weight": member["goal_weight"], "current_profile_weight": member["weight"]}
            if name == "get_training_preferences":
                return self._profile(db, member_id)["training_preferences"]
            if name == "get_weight_progress":
                rows = [dict(row) for row in db.execute("SELECT weight, logged_on FROM body_weight_logs WHERE member_id=? ORDER BY logged_on ASC, id ASC", (member_id,))]
                if not rows:
                    return {"message": "No body-weight entries have been logged yet.", "entries": [], "latest_weight": member["weight"], "goal_weight": member["goal_weight"]}
                latest, starting = rows[-1], rows[0]
                goal = member["goal_weight"]
                return {"entries": rows, "starting_weight": starting["weight"], "starting_date": starting["logged_on"], "latest_weight": latest["weight"], "latest_date": latest["logged_on"], "change": round(latest["weight"] - starting["weight"], 1), "goal_weight": goal, "distance_from_goal": round(goal - latest["weight"], 1) if goal is not None else None, "recent_trend": round(latest["weight"] - rows[max(0, len(rows)-4)]["weight"], 1)}
            if name == "get_recent_weight_logs":
                rows = [dict(row) for row in db.execute("SELECT weight, logged_on FROM body_weight_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT ?", (member_id, limit))]
                return {"entries": rows, "message": "No body-weight entries have been logged yet." if not rows else ""}
            if name == "get_workout_history":
                sessions = [dict(row) for row in db.execute("SELECT id, workout_name, workout_day, training_style, completed_at FROM workout_sessions WHERE member_id=? AND status='completed' ORDER BY completed_at DESC, id DESC LIMIT ?", (member_id, limit))]
                for session in sessions:
                    session["sets"] = [dict(row) for row in db.execute("SELECT exercise_name, actual_weight, actual_reps FROM workout_sets WHERE session_id=? AND completed=1 ORDER BY exercise_order, set_number", (session["id"],))]
                return {"sessions": sessions, "message": "No completed workouts are logged yet." if not sessions else ""}
            if name == "get_recent_exercises":
                rows = db.execute("SELECT workout_sets.exercise_name, MAX(workout_sessions.completed_at) last_performed, COUNT(*) completed_sets FROM workout_sets JOIN workout_sessions ON workout_sessions.id=workout_sets.session_id WHERE workout_sessions.member_id=? AND workout_sessions.status='completed' AND workout_sets.completed=1 GROUP BY lower(workout_sets.exercise_name) ORDER BY last_performed DESC LIMIT ?", (member_id, limit)).fetchall()
                return {"exercises": [dict(row) for row in rows], "message": "No completed exercise history is logged yet." if not rows else ""}
            if name == "search_exercises":
                query, muscle, equipment = arguments.get("query", "").lower(), arguments.get("muscle", "").lower(), arguments.get("equipment", "").lower()
                items = load_exercises()
                if query: items = [item for item in items if query in item.name.lower()]
                if muscle: items = [item for item in items if muscle in item.primary_muscles or muscle in item.secondary_muscles]
                if equipment: items = [item for item in items if equipment in item.equipment]
                return {"exercises": [{"name": item.name, "primary_muscles": item.primary_muscles, "equipment": item.equipment, "difficulty": item.difficulty} for item in items[:limit]]}
            if name == "get_training_plan":
                return self._training_plan(db, member)
            if name == "get_today_workout":
                session = db.execute("SELECT * FROM workout_sessions WHERE member_id=? AND status='active' ORDER BY started_at DESC LIMIT 1", (member_id,)).fetchone()
                if not session:
                    return {"message": "No active workout session."}
                sets = db.execute("SELECT exercise_name, set_number, target_reps, target_weight, target_rpe, actual_weight, actual_reps, completed FROM workout_sets WHERE session_id=? ORDER BY exercise_order, set_number", (session["id"],)).fetchall()
                return {"session": dict(session), "sets": [dict(row) for row in sets]}
            if name == "get_recent_workouts":
                rows = db.execute("SELECT workout_name, training_style, completed_at FROM workout_sessions WHERE member_id=? AND status='completed' ORDER BY completed_at DESC LIMIT ?", (member_id, limit)).fetchall()
                return [dict(row) for row in rows]
            if name in {"get_exercise_history", "get_progression", "get_saved_progression"}:
                exercise = arguments.get("exercise_name", "")
                if name == "get_saved_progression":
                    if not exercise.strip():
                        return {"message": "Choose an exercise name to look up its saved next-session target."}
                    state = db.execute("SELECT exercise_name, recommended_weight, recommended_reps, recommended_rpe, progression_action, reason, consecutive_misses, updated_at FROM exercise_progression_state WHERE member_id=? AND lower(exercise_name)=lower(?)", (member_id, exercise)).fetchone()
                    if not state:
                        # Resolve common wording such as “bench” only within this
                        # member's saved states; it never broadens the member scope.
                        keyword = next((word for word in re.findall(r"[a-z]{4,}", exercise.lower()) if word not in {"barbell", "powerlifting", "medium"}), "")
                        if keyword:
                            state = db.execute("SELECT exercise_name, recommended_weight, recommended_reps, recommended_rpe, progression_action, reason, consecutive_misses, updated_at FROM exercise_progression_state WHERE member_id=? AND lower(exercise_name) LIKE ? ORDER BY updated_at DESC LIMIT 1", (member_id, f"%{keyword}%")).fetchone()
                    return dict(state) if state else {"message": "No saved progression target exists for that exercise yet."}
                rows = db.execute("SELECT workout_sets.actual_weight, workout_sets.actual_reps, workout_sets.target_reps, workout_sets.completed, workout_sessions.completed_at, workout_sessions.training_style FROM workout_sets JOIN workout_sessions ON workout_sessions.id=workout_sets.session_id WHERE workout_sessions.member_id=? AND workout_sessions.status='completed' AND lower(workout_sets.exercise_name)=lower(?) ORDER BY workout_sessions.completed_at DESC, workout_sets.id DESC LIMIT ?", (member_id, exercise, limit)).fetchall()
                values = [dict(row) for row in rows]
                if name == "get_exercise_history":
                    return values or {"message": "No logged history for that exercise yet."}
                if not values:
                    return {"message": "No logged history yet; SYLRIX cannot calculate a progression recommendation."}
                latest = values[:3]
                target = latest[0].get("target_reps") or "5"
                recommendation = get_progression_recommendation(latest, f"3 sets × {target} reps", exercise, latest[0].get("training_style", ""))
                return {"recommendation": recommendation.message, "action": recommendation.action}
            if name == "get_pr_history":
                exercise = arguments.get("exercise_name", "").strip()
                query = "SELECT exercise_name, pr_type, value, weight, reps, estimated_1rm, achieved_at FROM personal_records WHERE member_id=?"
                params = [member_id]
                if exercise:
                    query += " AND lower(exercise_name) LIKE '%' || lower(?) || '%'"
                    params.append(exercise)
                all_records = [dict(row) for row in db.execute(query, params)]
                records = [dict(row) for row in db.execute(query + " ORDER BY achieved_at DESC, id DESC LIMIT ?", [*params, limit])]
                if not records:
                    return {"message": "No personal records have been established from completed workouts yet.", "records": [], "best_by_type": {}}
                best = {}
                for record in all_records:
                    key = record["pr_type"]
                    if key not in best or record["value"] > best[key]["value"]:
                        best[key] = record
                return {"records": records, "best_by_type": best}
            if name in {"get_nutrition_targets", "get_today_nutrition"}:
                summary = daily_nutrition(db, member)
                if name == "get_today_nutrition":
                    return summary
                targets = calculate_nutrition(member["age"], member["sex"], member["weight"], member["height"], member["goal"], member["days"])
                logged = db.execute("SELECT COALESCE(SUM(calories),0) calories, COALESCE(SUM(protein),0) protein, COALESCE(SUM(carbs),0) carbs, COALESCE(SUM(fat),0) fat FROM nutrition_logs WHERE member_id=? AND logged_on=?", (member_id, date.today().isoformat())).fetchone()
                return {"targets": targets, "today_logged": dict(logged)}
            if name == "get_recent_foods":
                return {"foods": [dict(row) for row in recent_foods(db, member_id, limit)], "message": "No foods have been logged yet." if not recent_foods(db, member_id, 1) else ""}
            if name == "get_today_summary":
                nutrition = daily_nutrition(db, member)
                workout = db.execute("SELECT workout_name, workout_day, status FROM workout_sessions WHERE member_id=? AND status='active' ORDER BY started_at DESC LIMIT 1", (member_id,)).fetchone()
                steps = db.execute("SELECT steps, goal FROM step_logs WHERE member_id=? AND logged_on=?", (member_id, date.today().isoformat())).fetchone()
                weight = db.execute("SELECT weight, logged_on FROM body_weight_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT 1", (member_id,)).fetchone()
                return {"workout": dict(workout) if workout else {"message": "No active workout."}, "nutrition": nutrition, "weight": dict(weight) if weight else {"weight": member["weight"]}, "steps": dict(steps) if steps else {"steps": 0, "goal": 8000}}
            if name == "get_nutrition_history":
                rows = db.execute(
                    """SELECT logged_on, COALESCE(SUM(calories), 0) calories, COALESCE(SUM(protein), 0) protein,
                       COALESCE(SUM(carbs), 0) carbs, COALESCE(SUM(fat), 0) fat, COALESCE(SUM(fiber), 0) fiber
                       FROM nutrition_logs WHERE member_id=? AND logged_on >= date('now', '-6 days')
                       GROUP BY logged_on ORDER BY logged_on DESC""", (member_id,)
                ).fetchall()
                daily = [dict(row) for row in rows]
                if not daily:
                    return {"message": "No nutrition entries have been logged in the last 7 days.", "days_logged": 0, "daily": [], "averages": {}}
                fields = ("calories", "protein", "carbs", "fat", "fiber")
                averages = {field: round(sum(row[field] for row in daily) / len(daily), 1) for field in fields}
                return {"days_logged": len(daily), "daily": daily, "averages": averages}
            if name == "get_steps":
                rows = db.execute("SELECT steps, goal, logged_on FROM step_logs WHERE member_id=? ORDER BY logged_on DESC LIMIT 7", (member_id,)).fetchall()
                return [dict(row) for row in rows] or {"message": "No step data logged yet."}
            if name == "get_progress_summary":
                workouts = db.execute(
                    """SELECT COUNT(DISTINCT workout_sessions.id) completed_workouts, COALESCE(SUM(workout_sets.actual_weight * workout_sets.actual_reps), 0) volume
                       FROM workout_sessions LEFT JOIN workout_sets ON workout_sets.session_id=workout_sessions.id
                       WHERE workout_sessions.member_id=? AND workout_sessions.status='completed'
                       AND workout_sessions.completed_at >= datetime('now', '-7 days')""", (member_id,)
                ).fetchone()
                recent_prs = [dict(row) for row in db.execute(
                    "SELECT exercise_name, pr_type, value, achieved_at FROM personal_records WHERE member_id=? AND achieved_at >= datetime('now', '-7 days') ORDER BY achieved_at DESC LIMIT 10", (member_id,)
                )]
                step_rows = db.execute("SELECT steps, goal FROM step_logs WHERE member_id=? AND logged_on >= date('now', '-6 days')", (member_id,)).fetchall()
                steps = {"days_logged": len(step_rows)}
                if step_rows:
                    steps.update({"average_steps": round(sum(row["steps"] for row in step_rows) / len(step_rows)), "goals_met": sum(row["steps"] >= row["goal"] for row in step_rows)})
                nutrition = self._tool(member_id, "get_nutrition_history", {})
                latest = db.execute(
                    """SELECT workout_sets.exercise_name, workout_sets.target_reps, workout_sessions.training_style
                       FROM workout_sets JOIN workout_sessions ON workout_sessions.id=workout_sets.session_id
                       WHERE workout_sessions.member_id=? AND workout_sessions.status='completed'
                       ORDER BY workout_sessions.completed_at DESC, workout_sets.id DESC LIMIT 1""", (member_id,)
                ).fetchone()
                progression = None
                if latest:
                    progression = self._tool(member_id, "get_progression", {"exercise_name": latest["exercise_name"]})
                return {"period_days": 7, "completed_workouts": workouts["completed_workouts"], "training_volume": workouts["volume"], "recent_prs": recent_prs, "steps": steps, "nutrition": nutrition, "latest_progression": progression}
            if name in {"find_exercise", "find_exercise_substitutes"}:
                exercise = self._exercise(arguments.get("exercise_name", ""))
                if not exercise:
                    return {"message": "No matching exercise exists in the local library."}
                if name == "find_exercise":
                    return {"name": exercise.name, "primary_muscles": exercise.primary_muscles, "secondary_muscles": exercise.secondary_muscles, "equipment": exercise.equipment, "movement_pattern": exercise.movement_pattern, "difficulty": exercise.difficulty}
                profile = UserProfile(TrainingGoal.from_text(member["goal"]), member["experience"], member["days"], f'{member["equipment"]} {member["equipment_notes"]}', limitations=member["limitations"], avoid_exercises=tuple(item.strip() for item in member["avoid_exercises"].split(",") if item.strip()))
                results = find_substitutes(exercise, load_exercises(), profile.equipment, profile)
                return [{"exercise": item.exercise.name, "score": item.score, "reason": item.reason} for item in results]
        return {"message": "That tool is unavailable."}

    def reply(self, member_id, message=None):
        """Reply for the member bound at construction; legacy calls still work."""
        if message is None:
            message, member_id = member_id, self.member_id
        if member_id is None:
            return "SYLRIX Coach needs an authenticated member profile before it can help."
        if self.tools is None or self.member_id != member_id:
            self.member_id = member_id
            self.tools = CoachToolRegistry(member_id, self._tool)
        if not self.configured:
            return self.local_reply(member_id, message)
        try:
            from openai import OpenAI
            with closing(self._connection()) as db:
                history = db.execute("SELECT role, message FROM coach_messages WHERE member_id=? ORDER BY id DESC LIMIT 20", (member_id,)).fetchall()
            context = [{"role": row["role"], "content": row["message"]} for row in reversed(history)]
            if not context or context[-1]["content"] != message:
                context.append({"role": "user", "content": message})
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            response = client.responses.create(model=MODEL, instructions=SYSTEM_INSTRUCTIONS, input=context, tools=self.tools.definitions)
            for _ in range(MAX_TOOL_ITERATIONS):
                calls = [item for item in getattr(response, "output", []) if getattr(item, "type", "") == "function_call"]
                if not calls:
                    return getattr(response, "output_text", "") or self.local_reply(member_id, message)
                outputs = []
                for call in calls:
                    try:
                        arguments = json.loads(getattr(call, "arguments", "{}") or "{}")
                        result = self.tools.execute(getattr(call, "name", ""), arguments)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        result = {"message": "The requested Coach tool could not be read safely."}
                    outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})
                response = client.responses.create(model=MODEL, instructions=SYSTEM_INSTRUCTIONS, input=outputs, previous_response_id=getattr(response, "id", None), tools=self.tools.definitions)
            self.last_error = "tool_iteration_limit"
            return "I could not complete that data lookup safely. Try a more specific question."
        except Exception as error:
            # Keep a non-user-facing diagnostic category; never return provider details.
            self.last_error = f"provider_unavailable:{type(error).__name__}"
            # Keep Coach useful during provider outages or exhausted credits.
            return self.local_reply(member_id, message)
