import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as sylrix


class DeploymentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        self.original_csrf = sylrix.csrf_enabled
        self.original_beta = sylrix.app.config["BETA_MODE"]
        sylrix.DATABASE = Path(self.directory.name) / "deployment.db"
        sylrix.setup_database()
        self.client = sylrix.app.test_client()

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        sylrix.csrf_enabled = self.original_csrf
        sylrix.app.config["BETA_MODE"] = self.original_beta
        self.directory.cleanup()

    def test_health_and_branded_not_found_are_safe(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})
        missing = self.client.get("/not-a-route")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"This page is not here", missing.data)
        self.assertNotIn(b"Traceback", missing.data)

    def test_csrf_rejects_missing_token_and_accepts_rendered_token(self):
        sylrix.csrf_enabled = True
        self.assertEqual(self.client.post("/register", data={}).status_code, 403)
        self.assertEqual(self.client.get("/register").status_code, 200)
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        response = self.client.post("/register", data={
            "csrf_token": token,
            "username": "beta_member",
            "email": "member@example.test",
            "password": "safe-password-123",
        })
        self.assertEqual(response.status_code, 302)

    def test_beta_mode_requires_configured_invite(self):
        sylrix.csrf_enabled = False
        sylrix.app.config["BETA_MODE"] = True
        with patch.dict("os.environ", {"SYLRIX_BETA_INVITE_CODE": "invite-only"}):
            denied = self.client.post("/register", data={"username": "beta_member", "email": "member@example.test", "password": "safe-password-123"})
            self.assertEqual(denied.status_code, 200)
            self.assertIn(b"invite code", denied.data)
            allowed = self.client.post("/register", data={"invite_code": "invite-only", "username": "beta_member", "email": "member@example.test", "password": "safe-password-123"})
        self.assertEqual(allowed.status_code, 302)


if __name__ == "__main__":
    unittest.main()
