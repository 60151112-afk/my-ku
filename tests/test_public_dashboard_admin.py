from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from quant_trader.public_dashboard_admin import (
    PROFILE_CHOICES,
    admin_password_configured,
    authenticate_admin_password,
    build_admin_command,
    resolve_project_path,
)


class PublicDashboardAdminTests(unittest.TestCase):
    def test_password_auth_plain_and_hash(self) -> None:
        self.assertFalse(admin_password_configured(env={}))
        self.assertTrue(admin_password_configured(env={"PUBLIC_DASHBOARD_ADMIN_PASSWORD": "secret"}))
        self.assertTrue(authenticate_admin_password("secret", env={"PUBLIC_DASHBOARD_ADMIN_PASSWORD": "secret"}))
        self.assertFalse(authenticate_admin_password("bad", env={"PUBLIC_DASHBOARD_ADMIN_PASSWORD": "secret"}))

        digest = hashlib.sha256(b"secret").hexdigest()
        self.assertTrue(authenticate_admin_password("secret", env={"PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256": digest}))

    def test_path_resolution_stays_inside_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = resolve_project_path(root, "config/example.json", must_be_json=True)
            self.assertEqual(root / "config" / "example.json", path)
            with self.assertRaises(ValueError):
                resolve_project_path(root, "../outside.json", must_be_json=True)
            with self.assertRaises(ValueError):
                resolve_project_path(root, "config/example.txt", must_be_json=True)

    def test_admin_command_whitelist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "quant_trader").mkdir()
            (root / "quant_trader" / "main.py").write_text("", encoding="utf-8")
            command = build_admin_command(
                "china_screen",
                project_root=root,
                python="python",
                config_path="config/china_stock_screener_latest.json",
                top=5,
                profile=PROFILE_CHOICES[0],
            )
            self.assertIn("china-screen", command)
            self.assertIn("--failure-policy", command)
            with self.assertRaises(KeyError):
                build_admin_command("anything_else", project_root=root)
            with self.assertRaises(PermissionError):
                build_admin_command("update_public_site", project_root=root, allow_push=False, no_push=False)


if __name__ == "__main__":
    unittest.main()
