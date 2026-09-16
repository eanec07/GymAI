import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as sylrix
from services.ai_coach import CoachService
from services.nutrition_tracking import daily_nutrition


class NutritionV2Tests(unittest.TestCase):
    def setUp(self):
        self.today = date.today().isoformat()
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        sylrix.DATABASE = Path(self.directory.name) / "nutrition.db"
        sylrix.setup_database()
        with sylrix.db_connection() as db:
            self.member_id = db.execute("INSERT INTO members (name,age,sex,weight,height,goal,days,equipment,experience) VALUES ('Food One',30,'male',180,70,'strength',3,'full gym','beginner')").lastrowid
            self.other_id = db.execute("INSERT INTO members (name,age,sex,weight,height,goal,days,equipment,experience) VALUES ('Food Two',30,'female',140,65,'muscle gain',3,'dumbbell','beginner')").lastrowid
            self.account_id = db.execute("INSERT INTO accounts (username,email,password_hash,member_id) VALUES ('food_one','one@food.test',?,?)", (generate_password_hash('safe-password-123'), self.member_id)).lastrowid
        self.client = sylrix.app.test_client()
        with self.client.session_transaction() as session: session['account_id'] = self.account_id

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        self.directory.cleanup()

    def _food(self, name="Breakfast", protein="30", calories="500"):
        return {"food_name": name, "serving": "1 serving", "calories": calories, "protein": protein, "carbs": "50", "fat": "12", "fiber": "8", "logged_on": self.today}

    def test_add_totals_remaining_recent_foods_and_dashboard_are_scoped(self):
        self.assertEqual(self.client.post('/nutrition', data=self._food()).status_code, 302)
        self.client.post('/nutrition', data=self._food('Lunch', '40', '700'))
        with sylrix.db_connection() as db:
            db.execute("INSERT INTO nutrition_logs (member_id,food_name,calories,protein,carbs,fat,fiber,logged_on) VALUES (?, 'Other food', 900, 90, 1, 1, 1, ?)", (self.other_id, self.today))
            member = db.execute("SELECT * FROM members WHERE id=?", (self.member_id,)).fetchone()
            summary = daily_nutrition(db, member, self.today)
        self.assertEqual(summary['consumed']['calories'], 1200)
        self.assertEqual(summary['consumed']['protein'], 70)
        self.assertEqual(summary['remaining']['protein'], summary['targets']['protein'] - 70)
        page = self.client.get(f'/nutrition?date={self.today}')
        self.assertIn(b'Breakfast', page.data); self.assertNotIn(b'Other food', page.data)
        self.assertIn(b'calories remaining', self.client.get('/app').data)

    def test_edit_delete_and_other_member_entries_are_protected(self):
        self.client.post('/nutrition', data=self._food())
        with sylrix.db_connection() as db:
            own = db.execute("SELECT id FROM nutrition_logs WHERE member_id=?", (self.member_id,)).fetchone()['id']
            other = db.execute("INSERT INTO nutrition_logs (member_id,food_name,calories,protein,carbs,fat,fiber,logged_on) VALUES (?, 'Private', 100, 10, 1, 1, 1, '2026-09-15')", (self.other_id,)).lastrowid
        edited = self._food('Edited', '35', '550')
        self.assertEqual(self.client.post(f'/nutrition/{own}/edit', data=edited).status_code, 302)
        self.assertEqual(self.client.post(f'/nutrition/{other}/edit', data=edited).status_code, 404)
        self.assertEqual(self.client.post(f'/nutrition/{other}/delete', data={'logged_on':'2026-09-15'}).status_code, 404)
        self.assertEqual(self.client.post(f'/nutrition/{own}/delete', data={'logged_on':'2026-09-15'}).status_code, 302)

    def test_weight_sync_and_coach_today_nutrition_are_member_bound(self):
        self.client.post('/progress/weight', data={'weight':'175.5', 'logged_on':self.today})
        self.client.post('/nutrition', data=self._food())
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute('SELECT weight FROM members WHERE id=?', (self.member_id,)).fetchone()['weight'], 175.5)
        coach = CoachService(sylrix.DATABASE, self.member_id)
        result = coach.tools.execute('get_today_nutrition', {'member_id': self.other_id})
        self.assertEqual(result['consumed']['protein'], 30)
        with patch('services.ai_coach.COACH_MODE', 'local'):
            self.assertIn('remaining', coach.reply('How much protein do I have left today?'))

    def test_invalid_nutrition_is_rejected(self):
        invalid = self._food(); invalid['calories'] = '-1'
        self.client.post('/nutrition', data=invalid)
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM nutrition_logs WHERE member_id=?', (self.member_id,)).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
