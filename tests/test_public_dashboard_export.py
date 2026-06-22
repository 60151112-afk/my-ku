from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from quant_trader.public_dashboard_export import (
    build_public_dashboard_bundle,
    export_public_dashboard_bundle,
)


class PublicDashboardExportTests(unittest.TestCase):
    def test_export_sanitizes_local_paths_and_commands(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_root = root / "outputs" / "china_realtime_screen"
            output_root.mkdir(parents=True)
            (output_root / "dashboard_data_pipeline_diagnosis_latest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-22T10:00:00+08:00",
                        "summary": {
                            "status": "warning",
                            "status_label": "数据链路需复核",
                            "quote_date": "2026-06-22",
                            "safe_refresh_command": (
                                r"C:\Local\Research\Python310\python.exe "
                                r"C:\Local\Research\project\scripts\china_realtime_fresh_guard.py"
                            ),
                        },
                        "rows": [
                            {
                                "检查项": "行情摘要",
                                "证据路径": r"C:\Local\Research\project\data\china_a_share\realtime_quotes_summary.json",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (output_root / "dashboard_daily_review_cause_aggregation_latest.json").write_text(
                '{"summary":{"status":"ok","top_cause":"策略问题"},"rows":[{"原因":"第一行\n第二行","次数":2}]}',
                encoding="utf-8",
            )

            bundle = build_public_dashboard_bundle(project_root=root)
            serialized = json.dumps(bundle, ensure_ascii=False)

            self.assertEqual(bundle["site_type"], "public_read_only_dashboard")
            self.assertIn("realtime_quotes_summary.json", serialized)
            self.assertIn("[已隐藏：本地执行命令]", serialized)
            self.assertNotIn(r"C:\Local\Research", serialized)
            self.assertNotIn("python.exe", serialized)
            self.assertEqual(bundle["sections"]["cause_aggregation"]["load_status"], "ok")

            output = root / "public_site" / "public_data" / "dashboard_public_latest.json"
            export_public_dashboard_bundle(bundle, output)
            self.assertTrue(output.exists())
            self.assertTrue(output.with_name("dashboard_public_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
