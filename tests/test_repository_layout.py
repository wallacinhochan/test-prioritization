import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayout(unittest.TestCase):
    def test_source_lock_points_to_versioned_inputs(self):
        lock = json.loads((ROOT / "studies/commons-lang/source-lock.json").read_text())
        base = ROOT / "studies/commons-lang"
        self.assertEqual(len(lock["commit"]), 40)
        self.assertTrue((base / lock["revision_inventory"]).resolve().is_file())
        self.assertTrue((base / lock["environment"]).resolve().is_file())

    def test_new_and_historical_metric_entrypoints(self):
        for path in ("scripts/metricas.py", "evidencias/KAN-25/metricas.py"):
            result = subprocess.run(
                [sys.executable, "-B", str(ROOT / path), "--help"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CSV KAN-15", result.stdout)

    def test_preservation_documents_exist(self):
        for path in ("docs/ARQUITETURA.md", "docs/CONTINUIDADE.md",
                     "docs/ARTEFATOS-LOCAIS.md"):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
