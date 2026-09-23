"""Supplemental native tests of the installed executable, never a PATH substitute."""
import argparse
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


def required_executable(value):
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError("Required executable must exist at an absolute path: " + value)
    return path


class ProbeTests(unittest.TestCase):
    def invoke(self, *arguments, expected=0, executable=None):
        result = subprocess.run(
            [str(executable or OPTIONS.probe), *map(str, arguments)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
            env={**os.environ, "LC_ALL": "C"},
        )
        self.assertEqual(result.returncode, expected,
                         f"{arguments!r}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def raw(self, mode, *patterns):
        result = self.invoke("-quiet", "-unformated", mode, *patterns, HERE / "contact.pdb")
        return [line.split(":") for line in result.stdout.splitlines() if line]

    def test_version(self):
        self.assertEqual(self.invoke("-version").stdout.strip(), "probe.2.21.211221")

    def test_long_version_alias(self):
        result = self.invoke("--version")
        self.assertEqual(result.stdout.strip(), "probe.2.21.211221")
        self.assertEqual(result.stderr, self.invoke("-version").stderr)
        # Only the two explicit aliases are supported, not general normalization.
        for flag in ("--self", "--version-extra", "--help-extra"):
            with self.subTest(flag=flag):
                self.assertIn("unrecognized flag", self.invoke(flag, expected=1).stderr)

    def test_long_help_alias(self):
        result = self.invoke("--help")
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, self.invoke("-help").stderr)
        self.assertIn("Syntax: probe", result.stderr)
        self.assertIn("-SElf", result.stderr)

    def test_self_contact_statistics(self):
        output = self.invoke("-quiet", "-countdots", "-self", "all", HERE / "contact.pdb").stdout
        self.assertIn("selection: self", output)
        self.assertIn("atoms selected: 4", output)
        total = re.search(r"grand tot:\s+(\d+)", output)
        self.assertIsNotNone(total)
        self.assertGreater(int(total.group(1)), 0)
        area = re.search(r"contact surface area:\s+([0-9.]+) A\^2", output)
        self.assertIsNotNone(area)
        self.assertGreater(float(area.group(1)), 0)

    def test_once_direction_and_numeric_records(self):
        rows = self.raw("-once", "chainA", "chainB")
        self.assertGreater(len(rows), 0)
        for fields in rows:
            self.assertEqual(len(fields), 19)
            self.assertEqual(fields[1], "1->2")
            self.assertEqual(fields[3].strip().split()[:3], ["A", "1", "ALA"])
            self.assertEqual(fields[4].strip().split()[:3], ["B", "2", "GLY"])
            self.assertIn(fields[2], ("wc", "cc", "so", "bo", "hb"))
            self.assertTrue(all(math.isfinite(float(fields[i])) for i in (*range(5, 12), *range(14, 19))))

    def test_both_matches_two_single_directions(self):
        both = self.raw("-both", "chainA", "chainB")
        forward = self.raw("-once", "chainA", "chainB")
        reverse = self.raw("-once", "chainB", "chainA")
        self.assertGreater(len(forward), 0)
        self.assertGreater(len(reverse), 0)
        self.assertEqual({row[1] for row in both}, {"1->2", "2->1"})
        self.assertEqual(sorted(tuple(row[2:]) for row in both if row[1] == "1->2"),
                         sorted(tuple(row[2:]) for row in forward))
        self.assertEqual(sorted(tuple(row[2:]) for row in both if row[1] == "2->1"),
                         sorted(tuple(row[2:]) for row in reverse))

    def test_surface_coordinates(self):
        output = self.invoke("-quiet", "-out", "chainA", HERE / "contact.pdb").stdout
        self.assertIn("@master {surface}", output)
        self.assertIn("@dotlist", output)
        points = re.findall(r"^\{[^}]*\}gray\s+([-0-9.]+),([-0-9.]+),([-0-9.]+)$", output, re.M)
        self.assertGreater(len(points), 100)
        for point in points:
            self.assertTrue(all(math.isfinite(float(value)) and abs(float(value)) < 5 for value in point))

    def test_unselected_chain_has_no_contacts(self):
        self.assertEqual(self.raw("-once", "chainZ", "chainB"), [])

    def test_malformed_non_pdb_record(self):
        result = self.invoke("-quiet", "-countdots", "-self", "all", HERE / "invalid-record.pdb")
        # Upstream deliberately ignores unknown records and returns success for no atoms.
        self.assertEqual(result.stdout, "")
        self.assertIn("No atom data in input.", result.stderr)

    def test_missing_file_is_error(self):
        # Use the Conan test build directory, not a hard-coded /tmp on HarmonyOS.
        with tempfile.TemporaryDirectory(prefix="king-probe-", dir=Path.cwd()) as temporary:
            missing = Path(temporary) / "missing.pdb"
            result = self.invoke("-quiet", "-self", "all", missing, expected=1)
            self.assertIn("could not open file", result.stderr)
            self.assertIn("missing.pdb", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_platform_runtime(self):
        result = self.invoke(executable=OPTIONS.platform_probe)
        self.assertIn("PDB numeric parsing, formatting, distance and overflow checks passed", result.stdout)
        if OPTIONS.target_os == "OHOS":
            self.assertRegex(result.stdout, r"OHOS kernel=HarmonyOS machine=(aarch64|x86_64)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=required_executable, required=True)
    parser.add_argument("--platform-probe", type=required_executable, required=True)
    parser.add_argument("--target-os", required=True)
    OPTIONS = parser.parse_args()
    unittest.main(argv=[__file__], verbosity=2)
