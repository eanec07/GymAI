"""Optional OpenAI Responses API coach with deterministic member-data tools."""
import json
import os
import sqlite3

MODEL = os.environ.get("SYLRIX_AI_MODEL", "gpt-5.6-terra")

TOOL_DEFINITIONS = [
    {"type": "function", "name": "get_user_profile", "description": "Get the member's training profile.", "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "get_recent_workouts", "description": "Get recent logged workout entries.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
    {"type": "function", "name": "get_daily_nutrition", "description": "Get deterministic daily nutrition totals and targets.", "parameters": {"type": "object", "properties": {}}},
]


class CoachService:
    def __init__(self, database_path):
        self.database_path = database_path

    @property
    def configured(self):
        return bool(os.environ.get("OPENAI_API_KEY"))

    def _tool(self, member_id, name, arguments):
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            if name == "get_user_profile":
                row = db.execute("SELECT goal, training_style, experience, days, equipment, limitations FROM members WHERE id=?", (member_id,)).fetchone()
                return dict(row) if row else {}
            if name == "get_recent_workouts":
                limit = max(1, min(int(arguments.get("limit", 10)), 30))
                return [dict(row) for row in db.execute("SELECT exercise_name, weight, reps, sets, logged_on FROM workout_logs WHERE member_id=? ORDER BY id DESC LIMIT ?", (member_id, limit))]
            if name == "get_daily_nutrition":
                row = db.execute("SELECT COALESCE(SUM(calories),0) calories, COALESCE(SUM(protein),0) protein, COALESCE(SUM(carbs),0) carbs, COALESCE(SUM(fat),0) fat, COALESCE(SUM(fiber),0) fiber FROM nutrition_logs WHERE member_id=? AND logged_on=date('now')", (member_id,)).fetchone()
                return dict(row)
        return {"error": "Unknown tool"}

    def reply(self, member_id, message):
        if not self.configured:
            return None
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        instructions = "You are SYLRIX Coach. Use tools for member facts; never invent logged data. Give safe fitness guidance and do not make changes without confirmation."
        response = client.responses.create(model=MODEL, instructions=instructions, input=message, tools=TOOL_DEFINITIONS)
        calls = [item for item in response.output if item.type == "function_call"]
        if calls:
            outputs = [{"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(self._tool(member_id, call.name, json.loads(call.arguments or "{}")))} for call in calls]
            response = client.responses.create(model=MODEL, instructions=instructions, input=outputs, tools=TOOL_DEFINITIONS)
        return response.output_text
