#!/usr/bin/env python3
"""Exercise the installed Dhrystone CLI and its published reference values."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import tempfile
import unittest


def run_program(arguments, input_text="", cwd=None):
    """Run locally or on a connected HarmonyOS device; preserve exit status."""
    if not OPTIONS.hdc:
        return subprocess.run(arguments, input=input_text, text=True,
                              capture_output=True, cwd=cwd, timeout=120)
    command = " ".join(shlex.quote(str(arg)) for arg in arguments)
    command = "printf %s " + shlex.quote(input_text) + " | " + command
    if cwd:
        command = "cd " + shlex.quote(cwd) + " && " + command
    command = "( " + command + " ); result=$?; printf '\nDHRY_EXIT=%s\n' \"$result\""
    result = subprocess.run([OPTIONS.hdc, "shell", command], text=True,
                            capture_output=True, timeout=150)
    match = re.search(r"\nDHRY_EXIT=(\d+)\s*$", result.stdout)
    if result.returncode or not match:
        raise RuntimeError("hdc execution failed: " + result.stdout + result.stderr)
    return subprocess.CompletedProcess(arguments, int(match[1]),
                                       result.stdout[:match.start()], result.stderr)


def elf_interpreter(path):
    with open(path, "rb") as stream:
        header = stream.read(64)
        if header[:6] != b"\x7fELF\x02\x01":
            raise AssertionError("expected a little-endian ELF64 executable")
        machine = struct.unpack_from("<H", header, 18)[0]
        offset = struct.unpack_from("<Q", header, 32)[0]
        size, count = struct.unpack_from("<HH", header, 54)
        for index in range(count):
            stream.seek(offset + index * size)
            entry = stream.read(size)
            if struct.unpack_from("<I", entry)[0] == 3:
                stream.seek(struct.unpack_from("<Q", entry, 8)[0])
                value = stream.read(struct.unpack_from("<Q", entry, 32)[0])
                return machine, value.rstrip(b"\0").decode("ascii")
    raise AssertionError("missing ELF interpreter")


class DhrystoneTests(unittest.TestCase):
    def invoke(self, input_text="", *arguments, binary=None, cwd=None):
        return run_program([binary or OPTIONS.binary, *arguments], input_text, cwd)

    def assert_reference(self, result, runs):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Version 2.1", result.stdout)
        self.assertIn(f"Execution starts, {runs} runs", result.stdout)
        # Literal expected values transcribed from upstream dhry_1.c.
        expected = {
            "Int_Glob": ["5"], "Bool_Glob": ["1"],
            "Ch_1_Glob": ["A"], "Ch_2_Glob": ["B"],
            "Arr_1_Glob[8]": ["7"], "Arr_2_Glob[8][7]": [str(runs + 10)],
            "Discr": ["0", "0"], "Enum_Comp": ["2", "1"],
            "Int_Comp": ["17", "18"],
            "Str_Comp": ["DHRYSTONE PROGRAM, SOME STRING"] * 2,
            "Int_1_Loc": ["5"], "Int_2_Loc": ["13"],
            "Int_3_Loc": ["7"], "Enum_Loc": ["1"],
            "Str_1_Loc": ["DHRYSTONE PROGRAM, 1'ST STRING"],
            "Str_2_Loc": ["DHRYSTONE PROGRAM, 2'ND STRING"],
        }
        for name, values in expected.items():
            actual = re.findall(r"^\s*" + re.escape(name) + r":\s*([^\n\r]+)",
                                result.stdout, re.MULTILINE)
            self.assertEqual([value.strip() for value in actual], values, name)
        pointers = re.findall(r"^\s*Ptr_Comp:\s*(0x[0-9a-fA-F]+)",
                              result.stdout, re.MULTILINE)
        self.assertEqual(len(pointers), 2, "pointer output must retain 64-bit addresses")
        self.assertEqual(pointers[0], pointers[1])
        self.assertNotEqual(int(pointers[0], 16), 0)

    def test_version(self):
        result = self.invoke("", "--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("2.1", result.stdout)
        self.assertNotIn("Execution starts", result.stdout)

    def test_help(self):
        result = self.invoke("", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("stdin", result.stdout)

    def test_unknown_option(self):
        self.assertNotEqual(self.invoke("", "--invalid-option").returncode, 0)

    def test_one_iteration(self):
        result = self.invoke("1\n")
        self.assert_reference(result, 1)
        self.assertIn("Measured time too small", result.stdout)

    def test_multiple_iterations(self):
        self.assert_reference(self.invoke("10000\n"), 10000)

    def test_whitespace_input(self):
        self.assert_reference(self.invoke("  17 \t\n"), 17)

    def test_zero_rejected(self):
        self.assertNotEqual(self.invoke("0\n").returncode, 0)

    def test_negative_rejected(self):
        self.assertNotEqual(self.invoke("-1\n").returncode, 0)

    def test_junk_rejected(self):
        for value in ("abc\n", "12junk\n", "1 2\n", "1" + " " * 126 + "junk\n"):
            with self.subTest(value=value):
                self.assertNotEqual(self.invoke(value).returncode, 0)

    def test_overflow_rejected(self):
        for value in ("2147483647\n", "999999999999999999999999999\n", "1" * 200 + "\n"):
            with self.subTest(value=value):
                self.assertNotEqual(self.invoke(value).returncode, 0)

    def test_eof_rejected(self):
        self.assertNotEqual(self.invoke().returncode, 0)

    def test_measured_rate(self):
        # Reach the upstream two-second validity threshold without assuming CPU speed.
        for runs in (10000000, 40000000, 160000000, 640000000):
            result = self.invoke(f"{runs}\n")
            self.assert_reference(result, runs)
            match = re.search(r"Dhrystones per Second:\s*([0-9.]+)", result.stdout)
            if match:
                rate = float(match[1])
                self.assertTrue(math.isfinite(rate) and rate > 0)
                print(f"MEASUREMENT runs={runs} dhrystones_per_second={rate}", flush=True)
                return
        self.fail("no valid two-second measurement within the safe iteration bound")

    @unittest.skipUnless(os.environ.get("DHRYSTONE_TEST_OHOS") == "1", "requires HarmonyOS")
    def test_ohos_loader_and_sandbox(self):
        machine, interpreter = elf_interpreter(OPTIONS.elf_file or OPTIONS.binary)
        expected = {183: "/lib/ld-musl-aarch64.so.1", 62: "/lib/ld-musl-x86_64.so.1"}
        self.assertIn(machine, expected)
        self.assertEqual(interpreter, expected[machine])
        # The HDC shell cannot directly open /lib; query the loaded libc in a probe.
        self.assertTrue(OPTIONS.probe, "HarmonyOS runtime probe is required")
        linked = run_program([OPTIONS.probe])
        self.assertEqual(linked.returncode, 0, linked.stdout + linked.stderr)
        self.assertIn("OHOS_RUNTIME_OK", linked.stdout)
        if OPTIONS.hdc:
            sandbox = OPTIONS.device_tmp.rstrip("/") + "/dhrystone space-中文-" + str(os.getpid())
            created = run_program(["mkdir", "-p", sandbox])
            self.assertEqual(created.returncode, 0)
            try:
                self.assert_reference(self.invoke("123\n", cwd=sandbox), 123)
            finally:
                removed = run_program(["rmdir", sandbox])
                self.assertEqual(removed.returncode, 0, removed.stdout)
        else:
            parent = os.environ.get("TMPDIR") or str(Path.home())
            with tempfile.TemporaryDirectory(prefix="dhrystone space-中文-", dir=parent) as sandbox:
                binary = str(Path(sandbox) / "dhrystone")
                shutil.copy2(OPTIONS.binary, binary)
                self.assert_reference(self.invoke("123\n", binary=binary, cwd=sandbox), 123)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--elf-file")
    parser.add_argument("--probe")
    parser.add_argument("--hdc")
    parser.add_argument("--device-tmp", default="/data/local/tmp")
    OPTIONS, remaining = parser.parse_known_args()
    result = unittest.main(argv=[__file__, *remaining], exit=False, verbosity=2).result
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
        "executed": True, "passed": result.wasSuccessful(),
        "runtime_executed": True, "tests": result.testsRun,
        "failed": len(result.failures) + len(result.errors), "skipped": len(result.skipped),
    }))
    raise SystemExit(0 if result.wasSuccessful() else 1)
