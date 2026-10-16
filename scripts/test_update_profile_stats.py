"""Check profile refresh behavior without making network requests."""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("update-profile-stats.py")
SPEC = importlib.util.spec_from_file_location("profile_stats", SCRIPT)
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)
SVG = f"{{{stats.SVG}}}"


class ProfileRefreshTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.profile = self.root / "profile"
        shutil.copytree(SCRIPT.parents[1] / "profile", self.profile)
        self.banners = sorted(self.profile.glob("banner-*.svg"))
        self.before = {path: path.read_bytes() for path in self.banners}

    def refresh(self):
        with patch.object(stats, "__file__", str(self.root / "scripts/update-profile-stats.py")):
            with patch.object(sys, "argv", [str(SCRIPT), "swimmwatch"]):
                stats.main()

    def test_public_metrics_include_all_pages_and_exclude_forks_and_private_repos(self):
        original = {"fork": False, "private": False, "stargazers_count": 8, "forks_count": 2}
        fork = {**original, "fork": True, "stargazers_count": 900}
        private = {**original, "private": True, "stargazers_count": 800}
        responses = [{"public_repos": 102, "followers": 7}, [original] + [fork] * 99, [original, private]]
        with patch.object(stats, "fetch", side_effect=responses) as fetch:
            self.refresh()
        self.assertIn("page=2", fetch.call_args_list[-1].args[0])
        self.assertEqual(len(self.banners), 6)
        for path in self.banners:
            with self.subTest(banner=path.name):
                root = ET.parse(path).getroot()
                summaries = root.findall(f"{SVG}g[@id='profile-summary']")
                self.assertEqual(len(summaries), 1)
                texts = [node.text for node in summaries[0].findall(f"{SVG}text")]
                self.assertEqual(texts[1:9], ["102", "Public repos", "16", "Stars", "4", "Forks", "7", "Followers"])
                original_root = ET.fromstring(self.before[path])
                original_root.remove(original_root.find(f"{SVG}g[@id='profile-summary']"))
                root.remove(summaries[0])
                self.assertEqual(ET.tostring(root), ET.tostring(original_root))

    def test_api_failure_preserves_every_banner(self):
        with patch.object(stats, "fetch", side_effect=RuntimeError("API unavailable")):
            with self.assertRaisesRegex(RuntimeError, "API unavailable"):
                self.refresh()
        self.assertEqual(self.before, {path: path.read_bytes() for path in self.banners})

    def test_invalid_language_source_preserves_every_banner(self):
        (self.profile / "top-langs.svg").write_text(f'<svg xmlns="{stats.SVG}"/>')
        with patch.object(stats, "fetch") as fetch:
            with self.assertRaises(ValueError):
                self.refresh()
            fetch.assert_not_called()
        self.assertEqual(self.before, {path: path.read_bytes() for path in self.banners})

    def test_repeated_generation_does_not_duplicate_content(self):
        metrics = [("Public repos", 12), ("Stars", 24), ("Forks", 3), ("Followers", 5)]
        languages = stats.read_languages(self.profile / "top-langs.svg")
        for path in self.banners:
            with self.subTest(banner=path.name):
                first = stats.render_banner(path, metrics, languages, "2026-10-16")
                path.write_text(first)
                self.assertEqual(stats.render_banner(path, metrics, languages, "2026-10-16"), first)

    def test_api_requests_use_workflow_token(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch.object(stats, "urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value.read.return_value = b"{}"
                stats.fetch("/users/swimmwatch")
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, "https://api.github.com/users/swimmwatch")
                self.assertEqual(request.get_header("Authorization"), "Bearer test-token")


if __name__ == "__main__":
    unittest.main()
