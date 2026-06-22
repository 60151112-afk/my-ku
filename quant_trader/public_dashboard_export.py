from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = Path("outputs") / "china_realtime_screen"
DEFAULT_PUBLIC_OUTPUT = Path("public_site") / "public_data" / "dashboard_public_latest.json"

ARTIFACTS: dict[str, str] = {
    "data_pipeline": "dashboard_data_pipeline_diagnosis_latest.json",
    "daily_review": "dashboard_daily_review_package_latest.json",
    "cause_aggregation": "dashboard_daily_review_cause_aggregation_latest.json",
    "loss_attribution": "dashboard_loss_attribution_latest.json",
    "strategy_traffic_light": "dashboard_strategy_traffic_light_latest.json",
    "health_score": "dashboard_health_score_latest.json",
    "next_actions": "dashboard_next_actions_latest.json",
    "next_trade_observation_review": "next_trade_observation_review_latest.json",
}

ARTIFACT_TITLES: dict[str, str] = {
    "data_pipeline": "数据链路诊断",
    "daily_review": "每日复盘",
    "cause_aggregation": "阻断原因分布",
    "loss_attribution": "亏损归因",
    "strategy_traffic_light": "策略红绿灯",
    "health_score": "面板健康分",
    "next_actions": "下一步动作",
    "next_trade_observation_review": "观察计划复核",
}

PATH_RE = re.compile(r"[A-Za-z]:\\[^\"'\n\r]+")
COMMAND_HINT_RE = re.compile(r"(python(?:\.exe)?|powershell|streamlit|\.ps1|\.py| --)", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"(token|secret|password|passwd|api[_-]?key|private|credential)", re.IGNORECASE)
PATH_KEY_RE = re.compile(r"(path|cwd|home|command|cmd|script|python|路径|命令|凭据|密钥)", re.IGNORECASE)


def _escape_newlines_inside_json_strings(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                out.append(char)
                escaped = False
                continue
            if char == "\\":
                out.append(char)
                escaped = True
                continue
            if char == '"':
                out.append(char)
                in_string = False
                continue
            if char == "\n":
                out.append("\\n")
                continue
            if char == "\r":
                out.append("\\r")
                continue
            out.append(char)
            continue
        out.append(char)
        if char == '"':
            in_string = True
    return "".join(out)


def _load_json_lenient(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return {}, f"read_failed: {exc}"
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        repaired = _escape_newlines_inside_json_strings(text)
        try:
            value = json.loads(repaired)
        except json.JSONDecodeError as repaired_exc:
            return {}, f"json_decode_failed: {exc}; repaired_failed: {repaired_exc}"
    if not isinstance(value, dict):
        return {}, "json_root_not_object"
    return value, None


def _filename_from_path_text(text: str) -> str:
    normalized = text.strip().strip('"')
    if not normalized:
        return ""
    normalized = normalized.replace("/", "\\")
    return normalized.rsplit("\\", 1)[-1] or "[已脱敏路径]"


def _sanitize_string(key: str, value: str) -> str:
    lowered = key.lower()
    if SECRET_KEY_RE.search(lowered):
        return "[已隐藏：敏感字段]"
    if PATH_RE.search(value):
        if COMMAND_HINT_RE.search(value) or PATH_KEY_RE.search(lowered):
            if COMMAND_HINT_RE.search(value):
                return "[已隐藏：本地执行命令]"
            return _filename_from_path_text(value)
        return PATH_RE.sub(lambda match: _filename_from_path_text(match.group(0)), value)
    if COMMAND_HINT_RE.search(value) and PATH_KEY_RE.search(lowered):
        return "[已隐藏：本地执行命令]"
    return value


def sanitize_public_value(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {str(item_key): sanitize_public_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [sanitize_public_value(item, key=key) for item in value]
    if isinstance(value, str):
        return _sanitize_string(key, value)
    return value


def _artifact_card(name: str, payload: dict[str, Any], source_path: Path, load_error: str | None) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else payload
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    sanitized_summary = sanitize_public_value(summary)
    status = str(sanitized_summary.get("status") or sanitized_summary.get("quote_status") or "unknown")
    return {
        "name": name,
        "title": ARTIFACT_TITLES.get(name, name),
        "source_file": source_path.name,
        "load_status": "ok" if load_error is None else "warning",
        "load_error": load_error,
        "generated_at": payload.get("generated_at") or sanitized_summary.get("generated_at") or "",
        "status": status,
        "status_label": sanitized_summary.get("status_label") or "",
        "quote_date": sanitized_summary.get("quote_date") or payload.get("quote_date") or "",
        "row_count": len(rows),
        "summary": sanitized_summary,
    }


def _summary_cards(cards: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {card["name"]: card for card in cards}
    daily = by_name.get("daily_review", {}).get("summary", {})
    cause = by_name.get("cause_aggregation", {}).get("summary", {})
    pipeline = by_name.get("data_pipeline", {}).get("summary", {})
    health = by_name.get("health_score", {}).get("summary", {})
    traffic = by_name.get("strategy_traffic_light", {}).get("summary", {})
    return {
        "dashboard_status": daily.get("status_label") or daily.get("status") or pipeline.get("status_label") or pipeline.get("status") or "待刷新",
        "quote_date": daily.get("quote_date") or pipeline.get("quote_date") or traffic.get("quote_date") or "",
        "selected_count": daily.get("selected_count", ""),
        "top_cause": cause.get("top_cause") or "",
        "top_cause_ratio": cause.get("top_cause_ratio", ""),
        "health_score": health.get("score") or health.get("dashboard_health_score") or daily.get("dashboard_health_score") or "",
        "traffic_light": traffic.get("status_label") or traffic.get("status") or "",
        "pipeline_status": pipeline.get("status_label") or pipeline.get("status") or "",
    }


def build_public_dashboard_bundle(
    *,
    project_root: Path,
    source_root: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    artifact_root = (root / (source_root or DEFAULT_OUTPUT_ROOT)).resolve()
    generated = generated_at or datetime.now().astimezone()
    cards: list[dict[str, Any]] = []
    sections: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for name, filename in ARTIFACTS.items():
        path = artifact_root / filename
        if not path.exists():
            warnings.append(f"{ARTIFACT_TITLES.get(name, name)}缺少源文件：{filename}")
            payload: dict[str, Any] = {}
            load_error = "source_missing"
        else:
            payload, load_error = _load_json_lenient(path)
            if load_error:
                warnings.append(f"{ARTIFACT_TITLES.get(name, name)}读取异常：{load_error}")

        rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else payload
        sanitized_rows = sanitize_public_value(rows)
        sanitized_summary = sanitize_public_value(summary)
        cards.append(_artifact_card(name, payload, path, load_error))
        sections[name] = {
            "title": ARTIFACT_TITLES.get(name, name),
            "source_file": path.name,
            "load_status": "ok" if load_error is None else "warning",
            "load_error": load_error,
            "summary": sanitized_summary,
            "rows": sanitized_rows,
        }

    return {
        "schema_version": 1,
        "site_type": "public_read_only_dashboard",
        "generated_at": generated.isoformat(),
        "source_status": "warning" if warnings else "ok",
        "warnings": warnings,
        "public_notice": {
            "title": "只读公开快照",
            "body": "本页面仅展示本地量化研究面板导出的脱敏快照，不构成投资建议，不包含自动下单、券商连接或本机刷新命令。",
            "research_only": True,
            "not_investment_advice": True,
            "broker_contacted": False,
            "order_submission_attempted": False,
        },
        "summary": _summary_cards(cards),
        "cards": cards,
        "sections": sections,
    }


def export_public_dashboard_bundle(bundle: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_csv = output.with_name("dashboard_public_summary.csv")
    cards = bundle.get("cards") if isinstance(bundle.get("cards"), list) else []
    with summary_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["name", "title", "status", "status_label", "quote_date", "row_count", "load_status", "load_error"],
        )
        writer.writeheader()
        for card in cards:
            if isinstance(card, dict):
                writer.writerow({field: card.get(field, "") for field in writer.fieldnames})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a sanitized public read-only dashboard bundle.")
    parser.add_argument("--project-root", default=".", help="Project root containing outputs/china_realtime_screen.")
    parser.add_argument("--source-root", default=str(DEFAULT_OUTPUT_ROOT), help="Relative or absolute dashboard output directory.")
    parser.add_argument("--output", default=str(DEFAULT_PUBLIC_OUTPUT), help="Public JSON output path.")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root)
    source_root = Path(args.source_root)
    output = Path(args.output)
    if not output.is_absolute():
        output = project_root / output
    bundle = build_public_dashboard_bundle(project_root=project_root, source_root=source_root)
    export_public_dashboard_bundle(bundle, output)
    print(f"exported_public_dashboard={output}")
    print(f"source_status={bundle.get('source_status')}")
    for warning in bundle.get("warnings", []):
        print(f"warning={warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
