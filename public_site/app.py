from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path(__file__).resolve().parent / "public_data" / "dashboard_public_latest.json"


def _load_bundle() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {
            "source_status": "missing",
            "warnings": [f"未找到公开数据文件：{DATA_PATH.name}"],
            "public_notice": {
                "title": "只读公开快照",
                "body": "请先在项目根目录运行导出脚本生成脱敏公开数据。",
            },
            "summary": {},
            "sections": {},
            "cards": [],
        }
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _as_text(value: Any, fallback: str = "-") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _as_percent(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if 0 <= numeric <= 1:
        numeric *= 100
    return f"{numeric:.1f}%"


def _rows_frame(section: dict[str, Any], limit: int = 100) -> pd.DataFrame:
    rows = section.get("rows") if isinstance(section.get("rows"), list) else []
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.head(limit)


def _display_dataframe(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("当前快照没有可展示明细。")
        return
    try:
        st.dataframe(frame, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(frame, hide_index=True)


def _display_plotly(fig: Any) -> None:
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig)


def _cause_chart(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("没有阻断原因数据。")
        return
    numeric_cols = list(frame.select_dtypes(include="number").columns)
    text_cols = [column for column in frame.columns if column not in numeric_cols]
    if not numeric_cols or not text_cols:
        st.info("阻断原因表缺少可绘图字段。")
        return
    fig = px.bar(frame, x=text_cols[0], y=numeric_cols[0], text=numeric_cols[0], title="阻断原因分布")
    fig.update_layout(xaxis_title="", yaxis_title="", margin=dict(l=10, r=10, t=45, b=10))
    _display_plotly(fig)


def _section(title: str, section: dict[str, Any], *, chart: bool = False) -> None:
    st.subheader(title)
    summary = section.get("summary") if isinstance(section.get("summary"), dict) else {}
    cols = st.columns(4)
    cols[0].metric("状态", _as_text(summary.get("status_label") or summary.get("status")))
    cols[1].metric("行情日期", _as_text(summary.get("quote_date") or summary.get("review_date")))
    cols[2].metric("记录数", _as_text(section.get("row_count") or len(section.get("rows") or [])))
    cols[3].metric("读取状态", _as_text(section.get("load_status")))
    if section.get("load_error"):
        st.warning(_as_text(section.get("load_error")))
    frame = _rows_frame(section)
    if chart:
        _cause_chart(frame)
    _display_dataframe(frame)


def main() -> None:
    st.set_page_config(page_title="A股量化研究公开看板", layout="wide")
    bundle = _load_bundle()
    notice = bundle.get("public_notice") if isinstance(bundle.get("public_notice"), dict) else {}
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    sections = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}

    st.title("A股量化研究公开看板")
    st.caption("公开版只读页面，展示已脱敏的本地研究快照。")
    st.warning(
        _as_text(
            notice.get("body"),
            "本页面仅用于量化研究展示，不构成投资建议，不包含自动下单、券商连接或本机刷新命令。",
        )
    )

    warnings = bundle.get("warnings") if isinstance(bundle.get("warnings"), list) else []
    if warnings:
        with st.expander("数据快照警告", expanded=True):
            for item in warnings:
                st.write(f"- {_as_text(item)}")

    st.subheader("当前状态摘要")
    metric_cols = st.columns(6)
    metric_cols[0].metric("面板状态", _as_text(summary.get("dashboard_status")))
    metric_cols[1].metric("行情日期", _as_text(summary.get("quote_date")))
    metric_cols[2].metric("入选数量", _as_text(summary.get("selected_count")))
    metric_cols[3].metric("首要原因", _as_text(summary.get("top_cause")))
    metric_cols[4].metric("原因占比", _as_percent(summary.get("top_cause_ratio")))
    metric_cols[5].metric("健康分", _as_text(summary.get("health_score")))

    st.divider()
    tabs = st.tabs(["复盘总览", "原因与诊断", "策略与风控", "公开数据"])
    with tabs[0]:
        if "daily_review" in sections:
            _section("每日复盘", sections["daily_review"])
        if "next_trade_observation_review" in sections:
            _section("观察计划复核", sections["next_trade_observation_review"])
    with tabs[1]:
        if "cause_aggregation" in sections:
            _section("阻断原因分布", sections["cause_aggregation"], chart=True)
        if "data_pipeline" in sections:
            _section("数据链路诊断", sections["data_pipeline"])
    with tabs[2]:
        if "strategy_traffic_light" in sections:
            _section("策略红绿灯", sections["strategy_traffic_light"])
        if "loss_attribution" in sections:
            _section("亏损归因", sections["loss_attribution"])
        if "health_score" in sections:
            _section("面板健康分", sections["health_score"])
    with tabs[3]:
        st.write("下载的 JSON 已脱敏，可用于静态归档或部署平台刷新。")
        download_json = json.dumps(bundle, ensure_ascii=False, indent=2)
        try:
            st.download_button(
                "下载公开快照 JSON",
                data=download_json,
                file_name="dashboard_public_latest.json",
                mime="application/json",
                width="stretch",
            )
        except TypeError:
            st.download_button(
                "下载公开快照 JSON",
                data=download_json,
                file_name="dashboard_public_latest.json",
                mime="application/json",
            )
        cards = bundle.get("cards") if isinstance(bundle.get("cards"), list) else []
        _display_dataframe(pd.DataFrame(cards))


if __name__ == "__main__":
    main()
