from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from quant_trader.public_dashboard_admin import (
    PROFILE_CHOICES,
    admin_password_configured,
    authenticate_admin_password,
    full_china_cli_available,
    project_root_from,
    public_snapshot_summary,
    run_admin_command,
)


PROJECT_ROOT = project_root_from(Path(__file__).resolve())
DEFAULT_CONFIG = "config/china_stock_screener_latest.json"
PUBLIC_URL = "https://60151112-afk.github.io/my-ku/"


def _write_result(result: Any) -> None:
    if result.ok:
        st.success(f"{result.command_key} 执行成功")
    else:
        st.error(f"{result.command_key} 执行失败，returncode={result.returncode}")
    with st.expander("命令输出", expanded=not result.ok):
        st.code(f"$ {result.command_display}", language="powershell")
        if result.stdout:
            st.code(result.stdout[-6000:], language="text")
        if result.stderr:
            st.code(result.stderr[-6000:], language="text")


def _require_login() -> None:
    if not admin_password_configured():
        st.error("未配置管理密码。请先设置 PUBLIC_DASHBOARD_ADMIN_PASSWORD 或 PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256。")
        st.stop()
    if st.session_state.get("admin_authenticated"):
        return
    with st.form("login_form"):
        password = st.text_input("管理密码", type="password")
        submitted = st.form_submit_button("登录")
    if submitted and authenticate_admin_password(password):
        st.session_state["admin_authenticated"] = True
        st.rerun()
    if submitted:
        st.error("密码不正确。")
    st.stop()


def _run_button(label: str, command_key: str, **kwargs: Any) -> None:
    if st.button(label, type="primary"):
        with st.spinner("正在执行..."):
            result = run_admin_command(command_key, project_root=PROJECT_ROOT, **kwargs)
        _write_result(result)


def main() -> None:
    st.set_page_config(page_title="A股量化私有管理后台", layout="wide")
    st.title("A股量化私有管理后台")
    st.caption("私有后台只供本人使用；公网公开页仍保持只读。")
    st.warning("不要把这个管理后台无密码暴露到公网。它不会自动下单，也不连接券商，但可以触发本地选股和发布流程。")
    _require_login()

    summary = public_snapshot_summary(PROJECT_ROOT)
    cols = st.columns(5)
    cols[0].metric("公开页", "可访问")
    cols[1].metric("快照状态", str(summary.get("status") or "-"))
    cols[2].metric("行情日期", str(summary.get("quote_date") or "-"))
    cols[3].metric("入选数量", str(summary.get("selected_count") if summary.get("selected_count") != "" else "-"))
    cols[4].metric("生成时间", str(summary.get("generated_at") or "-"))
    st.link_button("打开公网看板", PUBLIC_URL)

    st.divider()
    tab_screen, tab_publish, tab_status = st.tabs(["选股运行", "公开发布", "状态与安全"])

    with tab_screen:
        st.subheader("受控选股运行")
        if not full_china_cli_available(PROJECT_ROOT):
            st.error("当前部署缺少完整 quant_trader/main.py，不能在这里运行选股。请在完整私有仓库或本机运行。")
        config_path = st.text_input("配置文件", DEFAULT_CONFIG)
        top = st.number_input("Top N", min_value=1, max_value=100, value=5, step=1)
        profile = st.selectbox("策略 Profile", PROFILE_CHOICES, index=PROFILE_CHOICES.index("low_price_potential"))
        as_of = st.text_input("截至日期 YYYY-MM-DD，可留空", "")
        python = st.text_input("Python 命令", "python")
        _run_button(
            "运行选股",
            "china_screen",
            python=python,
            config_path=config_path,
            top=int(top),
            profile=profile,
            as_of=as_of.strip(),
            timeout_seconds=1800,
        )

    with tab_publish:
        st.subheader("公开页发布")
        st.write("这些操作只处理脱敏公开快照，不会上传 data、outputs、.env 或券商配置。")
        commit_message = st.text_input("提交说明", "Update public dashboard snapshot")
        allow_push = os.environ.get("PUBLIC_DASHBOARD_ADMIN_ALLOW_PUSH") == "1"
        no_push = not allow_push
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            _run_button("生成公开快照", "export_public_snapshot", python="python")
        with col_b:
            _run_button("校验公开目录", "validate_public_site")
        with col_c:
            _run_button("打包静态站点", "build_static_package")
        with col_d:
            label = "更新并推送公网" if allow_push else "更新但不推送"
            _run_button(
                label,
                "update_public_site",
                commit_message=commit_message,
                no_push=no_push,
                allow_push=allow_push,
                timeout_seconds=1800,
            )
        if not allow_push:
            st.info("当前未设置 PUBLIC_DASHBOARD_ADMIN_ALLOW_PUSH=1，因此后台只会本地提交，不会推送。")

    with tab_status:
        st.subheader("安全边界")
        st.write(
            {
                "project_root": str(PROJECT_ROOT),
                "public_url": PUBLIC_URL,
                "full_china_cli_available": full_china_cli_available(PROJECT_ROOT),
                "broker_contacted": False,
                "order_submission_attempted": False,
                "research_only": True,
            }
        )
        st.write("上线建议：使用 HTTPS、强密码，并在云服务器层再加一层 Basic Auth、Cloudflare Access 或 VPN。")


if __name__ == "__main__":
    main()
