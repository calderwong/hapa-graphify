from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesktopAssetTests(unittest.TestCase):
    def test_desktop_contract_files_exist(self) -> None:
        self.assertTrue((ROOT / "desktop" / "package.json").exists())
        self.assertTrue((ROOT / "desktop" / "main.js").exists())
        self.assertTrue((ROOT / "desktop" / "preload.js").exists())
        self.assertTrue((ROOT / "bin" / "hapa-graphify-desktop.sh").exists())
        package = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["main"], "main.js")

    def test_desktop_main_starts_service_and_loads_ui(self) -> None:
        main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        self.assertIn("hapa_graphify", main)
        self.assertIn("serve", main)
        self.assertIn("/ui", main)
        self.assertIn("cwd: ROOT", main)

    def test_desktop_smoke_check(self) -> None:
        result = subprocess.run(
            [str(ROOT / "bin" / "hapa-graphify-desktop.sh"), "--check"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"], payload)


if __name__ == "__main__":
    unittest.main()
