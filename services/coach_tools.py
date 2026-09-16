"""Safe, provider-facing Coach tool registry.

The registry is deliberately constructed with one authenticated member ID. Tool
arguments never contain a member ID and cannot change that binding.
"""

def _definition(name, description, properties=None):
    return {"type": "function", "name": name, "description": description, "parameters": {"type": "object", "properties": properties or {}, "additionalProperties": False}, "strict": True}


EXERCISE_ARGUMENTS = {"exercise_name": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 30}}
TOOL_DEFINITIONS = [
    _definition("get_member_profile", "Safe profile for the signed-in athlete."),
    _definition("get_member_goals", "Goals, goal weight, and training objective."),
    _definition("get_training_preferences", "Training preferences."),
    _definition("get_today_workout", "Currently active workout."),
    _definition("get_today_readiness", "Today's member-owned readiness check-in and deterministic score."),
    _definition("get_readiness_history", "The member's most recent readiness scores.", {"limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("get_today_training_recommendation", "Deterministic, non-medical session guidance based on today's readiness and recent training."),
    _definition("get_recent_workouts", "Recent completed sessions.", {"limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("get_workout_history", "Completed sessions and their sets.", {"limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("get_recent_exercises", "Recently performed exercises.", {"limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("get_exercise_performance", "Logged performance for one exercise.", EXERCISE_ARGUMENTS),
    _definition("get_progression", "Deterministic next-session recommendation.", EXERCISE_ARGUMENTS),
    _definition("get_exercise_progression", "Saved deterministic next-session target for one exercise.", EXERCISE_ARGUMENTS),
    _definition("get_personal_records", "Recorded PRs.", EXERCISE_ARGUMENTS),
    _definition("get_recent_prs", "Recent verified personal records."),
    _definition("get_weight_progress", "Latest, starting, change, goal distance, and trend."),
    _definition("get_recent_weight_logs", "Recent body-weight entries.", {"limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("get_nutrition_summary", "Nutrition targets and recent logs."),
    _definition("get_today_nutrition", "Today's deterministic nutrition target, consumed amounts, and remaining amounts."),
    _definition("get_recent_foods", "The signed-in member's recently logged foods.", {"limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("get_today_summary", "Compact workout, nutrition, weight, steps, and progress summary."),
    _definition("get_recent_nutrition", "Recent nutrition totals."),
    _definition("get_steps", "Recent step totals."),
    _definition("get_progress_summary", "Compact recent progress summary."),
    _definition("get_training_progress_summary", "Compact deterministic training progress summary."),
    _definition("get_exercise_information", "Trusted local exercise metadata.", EXERCISE_ARGUMENTS),
    _definition("search_exercises", "Search the trusted local exercise library.", {"query": {"type": "string"}, "muscle": {"type": "string"}, "equipment": {"type": "string"}, "limit": EXERCISE_ARGUMENTS["limit"]}),
    _definition("find_exercise_substitutes", "Equipment-aware local substitutes.", EXERCISE_ARGUMENTS),
]
ALLOWED_TOOL_NAMES = {tool["name"] for tool in TOOL_DEFINITIONS}


class CoachToolRegistry:
    """Binds tools to one member before a model is ever invoked."""
    def __init__(self, member_id, executor):
        self.member_id = int(member_id)
        self._executor = executor

    @property
    def definitions(self):
        return TOOL_DEFINITIONS

    def execute(self, name, arguments=None):
        if name not in ALLOWED_TOOL_NAMES:
            return {"message": "That tool is unavailable."}
        arguments = dict(arguments or {})
        arguments.pop("member_id", None)
        return self._executor(self.member_id, name, arguments)
