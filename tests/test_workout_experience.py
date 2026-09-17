import tempfile
import unittest
from pathlib import Path
from werkzeug.security import generate_password_hash

import app as sylrix


class WorkoutExperienceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.original = sylrix.DATABASE
        sylrix.DATABASE = Path(self.directory.name) / 'workout.db'; sylrix.setup_database()
        with sylrix.db_connection() as db:
            self.member = db.execute("INSERT INTO members (name,age,sex,weight,height,goal,days,equipment,experience,training_style) VALUES ('Lift One',30,'male',180,70,'strength',3,'full gym','intermediate','powerlifting')").lastrowid
            self.other = db.execute("INSERT INTO members (name,age,sex,weight,height,goal,days,equipment,experience,training_style) VALUES ('Lift Two',30,'male',180,70,'strength',3,'full gym','intermediate','powerlifting')").lastrowid
            self.account = db.execute("INSERT INTO accounts (username,email,password_hash,member_id) VALUES ('lift_one','lift@one.test',?,?)", (generate_password_hash('safe-password-123'), self.member)).lastrowid
        self.client=sylrix.app.test_client()
        with self.client.session_transaction() as s:s['account_id']=self.account

    def tearDown(self): sylrix.DATABASE=self.original; self.directory.cleanup()

    def test_active_session_resumes_notes_are_scoped_and_warmups_do_not_count(self):
        self.assertEqual(self.client.get('/workout/1').status_code,200)
        self.assertEqual(self.client.get('/workout/1').status_code,200)
        with sylrix.db_connection() as db:
            session_id=db.execute("SELECT id FROM workout_sessions WHERE member_id=? AND status='active'",(self.member,)).fetchone()['id']
            self.assertEqual(db.execute("SELECT COUNT(*) FROM workout_sessions WHERE member_id=? AND status='active'",(self.member,)).fetchone()[0],1)
            warm=db.execute("SELECT id FROM workout_sets WHERE session_id=? AND is_warmup=1 LIMIT 1",(session_id,)).fetchone()
            working=db.execute("SELECT id FROM workout_sets WHERE session_id=? AND is_warmup=0 LIMIT 1",(session_id,)).fetchone()['id']
        if warm: self.client.post(f'/workout/session/{session_id}/set/{warm["id"]}',data={'weight':'45','reps':'5','rpe':''})
        self.client.post(f'/workout/session/{session_id}/set/{working}',data={'weight':'135','reps':'5','rpe':'8'})
        self.client.post(f'/workout/session/{session_id}/exercise/1/note',data={'notes':'Use safeties higher'})
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute("SELECT notes FROM session_exercises WHERE session_id=? AND exercise_order=1",(session_id,)).fetchone()['notes'],'Use safeties higher')
            self.assertEqual(db.execute("SELECT COUNT(*) FROM workout_sets WHERE session_id=? AND completed=1 AND is_warmup=0",(session_id,)).fetchone()[0],1)

    def test_other_member_cannot_mutate_set_or_finish_session(self):
        with sylrix.db_connection() as db:
            session_id=db.execute("INSERT INTO workout_sessions (member_id,workout_name,workout_day,status) VALUES (?, 'Private',1,'active')",(self.other,)).lastrowid
            set_id=db.execute("INSERT INTO workout_sets (session_id,exercise_name,exercise_order,set_number,target_reps,completed) VALUES (?, 'Bench',1,1,'5',0)",(session_id,)).lastrowid
        self.assertEqual(self.client.post(f'/workout/session/{session_id}/set/{set_id}',data={'weight':'100','reps':'5'}).status_code,404)
        self.assertEqual(self.client.post(f'/workout/session/{session_id}/finish',data={'confirm':'finish'}).status_code,404)
        self.assertEqual(self.client.post(f'/workout/session/{session_id}/exercise/1/replace',data={'exercise':'Bench'}).status_code,404)

    def test_active_workout_uses_canonical_exercise_detail_slug(self):
        self.client.get('/workout/1')
        with sylrix.db_connection() as db:
            session_id = db.execute("SELECT id FROM workout_sessions WHERE member_id=? AND status='active'", (self.member,)).fetchone()['id']
            db.execute("UPDATE session_exercises SET exercise_name='Bench Press - Powerlifting' WHERE session_id=? AND exercise_order=1", (session_id,))
            db.execute("UPDATE workout_sets SET exercise_name='Bench Press - Powerlifting' WHERE session_id=? AND exercise_order=1", (session_id,))
        page = self.client.get('/workout/1')
        self.assertIn(b'/exercises/bench-press-powerlifting', page.data)
        self.assertEqual(self.client.get('/exercises/bench-press-powerlifting').status_code, 200)


if __name__=='__main__': unittest.main()
