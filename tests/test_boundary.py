import json
from pathlib import Path
import unittest

from src.codex_broker import FEATURES_OFF, TOOLS, PROPOSE, SHELL


class PolicyTests(unittest.TestCase):
    def test_abstract_tool_surface(self):
        self.assertEqual([t["name"] for t in TOOLS], ["observe", "transition"])
        self.assertEqual(PROPOSE["name"], "propose")
        self.assertEqual(SHELL["name"], "terminal")
        for item in TOOLS + [PROPOSE]:
            encoded = json.dumps(item)
            for field in ('"pid"', '"path"', '"command"', '"process"', '"app"'):
                self.assertNotIn(field, encoded)

    def test_native_catalog_policy(self):
        path = Path(__file__).resolve().parents[1] / "src/model-policy.json"
        models = json.loads(path.read_text())["models"]
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["slug"], "gpt-6.1-sol")
        self.assertIsNone(models[0]["apply_patch_tool_type"])
        self.assertEqual(models[0]["experimental_supported_tools"], [])
        self.assertEqual(models[0]["tool_mode"], "direct")
        for flag in ("shell_tool", "unified_exec", "apps", "memories", "plugins", "multi_agent", "browser_use"):
            self.assertIn(flag, FEATURES_OFF)
