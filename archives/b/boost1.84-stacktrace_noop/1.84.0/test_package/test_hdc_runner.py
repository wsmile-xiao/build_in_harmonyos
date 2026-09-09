#!/usr/bin/env python3
"""Behavioral tests for the optional HDC target runner."""

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


RUNNER = Path(__file__).with_name("hdc_runner.py")
RECIPE = RUNNER.parent.parent / "conanfile.py"


class HdcRunnerTest(unittest.TestCase):
    def _fake_hdc(self, root: Path) -> tuple[Path, Path]:
        log = root / "hdc-calls.jsonl"
        fake = root / "fake_hdc.py"
        fake.write_text(
            """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ[\"FAKE_HDC_LOG\"]).open(\"a\", encoding=\"utf-8\") as stream:
    stream.write(json.dumps(args) + \"\\n\")

if args[:2] == [\"file\", \"send\"] and os.environ.get(\"FAKE_HDC_SEND_FAIL\"):
    print(\"[Fail]Error opening file: no such file or directory\")
    sys.exit(0)

if \"shell\" in args and \"__BOOST_NOOP_REMOTE_RC__\" in args[-1]:
    remote_rc = os.environ.get(\"FAKE_HDC_REMOTE_RC\", \"0\")
    print(\"fake HarmonyOS program output\")
    print(\"__BOOST_NOOP_REMOTE_RC__=\" + remote_rc)
sys.exit(0)
""",
            encoding="utf-8",
        )

        if os.name == "nt":
            launcher = root / "fake_hdc.cmd"
            launcher.write_text(
                f'@"{sys.executable}" "{fake}" %*\n', encoding="utf-8"
            )
        else:
            launcher = fake
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
        return launcher, log

    def test_success_sends_and_runs_target_binary(self) -> None:
        """Catches a runner that never sends or executes the target binary."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hdc, log = self._fake_hdc(root)
            binary = root / "noop_test"
            binary.write_bytes(b"ELF test fixture")
            env = os.environ.copy()
            env["FAKE_HDC_LOG"] = str(log)

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--hdc",
                    str(hdc),
                    "--remote-dir",
                    "/data/local/tmp/boost_noop_tdd",
                    "--label",
                    "noop_ho",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertTrue(
                any(call[:2] == ["file", "send"] for call in calls), calls
            )
            self.assertTrue(
                any("shell" in call and "./noop_ho" in call[-1] for call in calls),
                calls,
            )
            self.assertIn("fake HarmonyOS program output", result.stdout)

    def test_remote_nonzero_fails_when_hdc_itself_returns_zero(self) -> None:
        """Catches trusting HDC's local exit code over the remote program."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hdc, log = self._fake_hdc(root)
            binary = root / "noop_test"
            binary.write_bytes(b"ELF test fixture")
            env = os.environ.copy()
            env["FAKE_HDC_LOG"] = str(log)
            env["FAKE_HDC_REMOTE_RC"] = "23"

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--hdc",
                    str(hdc),
                    "--remote-dir",
                    "/data/local/tmp/boost_noop_tdd",
                    "--label",
                    "noop_ho",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("__BOOST_NOOP_REMOTE_RC__=23", result.stdout)

    def test_send_failure_text_fails_when_hdc_returns_zero(self) -> None:
        """Catches ignoring HDC transfer errors reported only in its output."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hdc, log = self._fake_hdc(root)
            binary = root / "noop_test"
            binary.write_bytes(b"ELF test fixture")
            env = os.environ.copy()
            env["FAKE_HDC_LOG"] = str(log)
            env["FAKE_HDC_SEND_FAIL"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--hdc",
                    str(hdc),
                    "--remote-dir",
                    "/data/local/tmp/boost_noop_tdd",
                    "--label",
                    "noop_ho",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("[Fail]Error opening file", result.stdout)


class RecipeBuildEnvironmentTest(unittest.TestCase):
    def test_upstream_links_use_conan_build_environment(self) -> None:
        """Catches bypassing profile buildenv when invoking OHOS lld."""
        spec = importlib.util.spec_from_file_location(
            "boost_stacktrace_noop_recipe", RECIPE
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Output:
            def info(self, _message):
                pass

        class Harness:
            def __init__(self, root: Path):
                self.source_folder = str(root / "source")
                self.build_folder = str(root / "build")
                Path(self.build_folder).mkdir()
                self.output = Output()
                self.conan_runs = []
                self.direct_runs = []

            def run(self, command, **kwargs):
                self.conan_runs.append((command, kwargs))
                return 0

            def _run_command(self, command, **kwargs):
                self.direct_runs.append((command, kwargs))
                return 0, "", ""

            def _target_command(self, executable, _label):
                return [executable]

        with tempfile.TemporaryDirectory() as tmp:
            harness = Harness(Path(tmp))
            module.BoostStacktraceNoopConan._run_upstream_tests(
                harness,
                "clang++",
                "-std=c++17 -stdlib=libc++",
                "libboost_stacktrace_noop.a",
            )

        self.assertEqual(len(harness.conan_runs), 6)
        self.assertTrue(
            all(call[1].get("ignore_errors") for call in harness.conan_runs)
        )
        self.assertEqual(len(harness.direct_runs), 6)
        self.assertTrue(
            all(not call[1].get("shell", False) for call in harness.direct_runs)
        )


if __name__ == "__main__":
    unittest.main()
