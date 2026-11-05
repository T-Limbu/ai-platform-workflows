"""Static checks on the reusable workflows (stdlib only, no network)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
FILES = ["youtube-extractor.yml", "render-release.yml", "layout-check.yml"]
ALLOWED_INLINE_RUN = {
    "run: ${{ inputs.install_command }}",
    "run: ${{ inputs.test_command }}",
    "run: ${{ inputs.build_command }}",
}


def read(name):
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def indent(line):
    return len(line) - len(line.lstrip(" "))


def run_block_lines(text):
    """Yield (lineno, line) for lines inside `run: |` blocks."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].strip() == "run: |":
            key_indent = indent(lines[i])
            i += 1
            while i < len(lines) and (not lines[i].strip() or indent(lines[i]) > key_indent):
                yield i + 1, lines[i]
                i += 1
        else:
            i += 1


class TestNoExpressionsInScripts(unittest.TestCase):
    def test_no_expression_inside_run_blocks(self):
        for name in FILES:
            for lineno, line in run_block_lines(read(name)):
                self.assertNotIn("${{", line, f"{name}:{lineno} pastes an expression into a script")

    def test_single_line_run_only_command_inputs(self):
        for name in FILES:
            for lineno, line in enumerate(read(name).split("\n"), 1):
                stripped = line.strip()
                if stripped.startswith("run:") and "${{" in stripped:
                    self.assertIn(stripped, ALLOWED_INLINE_RUN, f"{name}:{lineno}")


class TestRenderRelease(unittest.TestCase):
    def setUp(self):
        self.text = read("render-release.yml")

    def test_environment_gate(self):
        self.assertIn("environment: ${{ inputs.deploy_environment }}", self.text)
        self.assertRegex(self.text, r"deploy_environment:\n(?:.*\n)*?\s+default: 'production'")

    def test_job_permissions_contents_write(self):
        self.assertRegex(self.text, r"\n    permissions:\n      contents: write\n")

    def test_release_action_pinned_by_sha(self):
        self.assertRegex(self.text, r"softprops/action-gh-release@[0-9a-f]{40}\b")


class TestYoutubeExtractorWorkflow(unittest.TestCase):
    def setUp(self):
        self.text = read("youtube-extractor.yml")

    def test_no_old_repo_name(self):
        self.assertNotIn("squad-workflows/", self.text.replace(".squad-workflows", ""))
        self.assertNotIn("T-Limbu/squad-workflows", self.text)

    def test_installs_from_requirements(self):
        self.assertIn("pip install -r .squad-workflows/connectors/youtube/requirements.txt", self.text)

    def test_workflows_ref_input(self):
        self.assertIn("workflows_ref:", self.text)


class TestRequirements(unittest.TestCase):
    def test_google_genai_pinned(self):
        reqs = (ROOT / "connectors" / "youtube" / "requirements.txt").read_text()
        self.assertTrue(re.search(r"^google-genai==\d", reqs, re.M))


if __name__ == "__main__":
    unittest.main()
