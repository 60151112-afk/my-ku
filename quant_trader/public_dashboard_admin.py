from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROFILE_CHOICES = [
    "short_mid",
    "low_price_potential",
    "low_price_reversal_balanced",
    "high_win_defensive",
    "short_trend_start",
    "dragon_start",
    "integrated_alpha",
]


@dataclass(frozen=True)
class AdminCommandResult:
    command_key: str
    returncode: int
    stdout: str
    stderr: str
    command_display: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def project_root_from(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "public_site").exists() and (candidate / "quant_trader").exists():
            return candidate
    return current


def authenticate_admin_password(password: str, *, env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    expected = values.get("PUBLIC_DASHBOARD_ADMIN_PASSWORD", "")
    expected_hash = values.get("PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256", "")
    if expected:
        return password == expected
    if expected_hash:
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return digest.lower() == expected_hash.lower()
    return False


def admin_password_configured(*, env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return bool(values.get("PUBLIC_DASHBOARD_ADMIN_PASSWORD") or values.get("PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256"))


def resolve_project_path(project_root: Path, relative_path: str, *, must_be_json: bool = False) -> Path:
    if not relative_path:
        raise ValueError("Path is required.")
    normalized = relative_path.replace("\\", "/").lstrip("/")
    if ".." in Path(normalized).parts:
        raise ValueError("Parent-directory paths are not allowed.")
    resolved = (project_root / normalized).resolve()
    root = project_root.resolve()
    if not (resolved == root or root in resolved.parents):
        raise ValueError("Path must stay inside project root.")
    if must_be_json and resolved.suffix.lower() != ".json":
        raise ValueError("Only .json config files are allowed.")
    return resolved


def public_snapshot_summary(project_root: Path) -> dict[str, Any]:
    path = project_root / "public_site" / "public_data" / "dashboard_public_latest.json"
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "invalid", "path": str(path), "error": str(exc)}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "status": payload.get("source_status") or "unknown",
        "generated_at": payload.get("generated_at") or "",
        "quote_date": summary.get("quote_date") or "",
        "dashboard_status": summary.get("dashboard_status") or "",
        "selected_count": summary.get("selected_count", ""),
        "site_type": payload.get("site_type") or "",
    }


def full_china_cli_available(project_root: Path) -> bool:
    return (project_root / "quant_trader" / "main.py").exists()


def build_admin_command(
    command_key: str,
    *,
    project_root: Path,
    python: str = "python",
    config_path: str = "config/china_stock_screener_latest.json",
    top: int = 5,
    profile: str = "low_price_potential",
    failure_policy: str = "shrink_to_available",
    as_of: str = "",
    commit_message: str = "Update public dashboard snapshot",
    no_push: bool = False,
    allow_push: bool = False,
) -> list[str]:
    root = project_root.resolve()
    if command_key == "export_public_snapshot":
        return [
            python,
            "-m",
            "quant_trader.public_dashboard_export",
            "--project-root",
            str(root),
            "--output",
            "public_site/public_data/dashboard_public_latest.json",
        ]
    if command_key == "validate_public_site":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/validate_public_dashboard_static_site.ps1"]
    if command_key == "build_static_package":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/build_public_dashboard_static_package.ps1"]
    if command_key == "update_public_site":
        if not allow_push and not no_push:
            raise PermissionError("Push updates require PUBLIC_DASHBOARD_ADMIN_ALLOW_PUSH=1 or NoPush mode.")
        command = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/update_public_dashboard_and_push.ps1",
            "-Message",
            commit_message,
        ]
        if no_push:
            command.append("-NoPush")
        return command
    if command_key == "china_screen":
        if not full_china_cli_available(root):
            raise FileNotFoundError("quant_trader/main.py is required for private screening operations.")
        if profile not in PROFILE_CHOICES:
            raise ValueError(f"Unsupported profile: {profile}")
        if not 1 <= int(top) <= 100:
            raise ValueError("Top N must be between 1 and 100.")
        config = resolve_project_path(root, config_path, must_be_json=True)
        command = [
            python,
            "-m",
            "quant_trader.main",
            "china-screen",
            "--config",
            str(config),
            "--top",
            str(int(top)),
            "--profile",
            profile,
            "--failure-policy",
            failure_policy,
        ]
        if as_of:
            command.extend(["--as-of", as_of])
        return command
    raise KeyError(f"Unsupported admin command: {command_key}")


def run_admin_command(
    command_key: str,
    *,
    project_root: Path,
    timeout_seconds: int = 600,
    **kwargs: Any,
) -> AdminCommandResult:
    command = build_admin_command(command_key, project_root=project_root, **kwargs)
    completed = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        shell=False,
    )
    return AdminCommandResult(
        command_key=command_key,
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
        command_display=" ".join(_quote_part(part) for part in command),
    )


def _quote_part(part: str) -> str:
    if not part:
        return '""'
    if any(char.isspace() for char in part):
        return f'"{part}"'
    return part
