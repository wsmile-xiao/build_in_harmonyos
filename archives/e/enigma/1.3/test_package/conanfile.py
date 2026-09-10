#!/usr/bin/env python3
"""Conan test_package for enigma 1.3 — runs the Crypt::Enigma API test.

Executes test_enigma.py (which drives test_crypt_enigma.pl against the
packaged Crypt/Enigma.pm), parses the real assertion counts from its
output, and emits the HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT
evidence markers. Any count mismatch or missing evidence fails the test.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class EnigmaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # HMBS readonly_tmp: /tmp is read-only on HarmonyOS workers.
        # Mirror the main recipe: prefer the hmbs-injected writable
        # TMPDIR/TMP/TEMP so perl/File::Temp/sh inherit a writable temp dir.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("enigma_test_env")

    def _find_perl(self):
        found = shutil.which("perl")
        if found:
            return found
        for candidate in (
            "/data/service/hnp/bin/perl",
            "/usr/bin/perl",
            "/usr/local/bin/perl",
        ):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _emit_upstream_result(self, dep):
        """Re-emit the parsed `make test` evidence persisted by package()."""
        candidates = (
            os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
            os.path.join(dep.package_folder, "upstream_test_result.json"),
        )
        for path in candidates:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
            ok_shape = (
                isinstance(result, dict)
                and result.get("status") == "passed"
                and int(result.get("discovered", 0)) > 0
                and int(result.get("executed", 0)) == int(result.get("discovered", 0))
                and int(result.get("passed", 0)) == int(result.get("discovered", 0))
                and int(result.get("failed", 0)) == 0
                and int(result.get("skipped", 0)) == 0
            )
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
            if not ok_shape:
                raise ConanException(f"upstream test evidence invalid: {result}")
            return
        raise ConanException("upstream_test_result.json not found in package")

    def test(self):
        dep = self.dependencies["enigma"]
        script = os.path.join(self.recipe_folder, "test_enigma.py")
        perl = self._find_perl()
        if not perl:
            raise ConanException("perl interpreter not found for test_package")

        # Do not rely on self.run()'s stdout return value: on the
        # read-only-/tmp worker it came back empty even though the driver
        # itself printed ENIGMA_TEST_RESULT passed=18 total=18 with rc=0
        # (same phenomenon already worked around in build() via make_test.log).
        # Capture combined stdout+stderr to a file inside build_folder
        # (always writable; never /tmp) and parse that file instead.
        try:
            os.makedirs(self.build_folder, exist_ok=True)
        except Exception:
            pass
        log_path = os.path.join(self.build_folder, "test_enigma.log")
        rc_out = None
        try:
            rc_out = self.run(
                '"{0}" "{1}" "{2}" > "{3}" 2>&1'.format(perl, script, dep.package_folder, log_path),
                env="conanrun",
                stdout=True,
            )
        except ConanException:
            # Non-zero exit: the captured log below still holds the TAP
            # trace and counts. Fall through to parse it.
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        out = out or (rc_out or "")
        self.output.info("test output:\n" + out)

        match = re.search(r"ENIGMA_TEST_RESULT\s+passed=(\d+)\s+total=(\d+)", out)
        if match:
            passed_count, discovered = int(match.group(1)), int(match.group(2))
        else:
            plan = re.search(r"^1\.\.(\d+)\s*$", out, re.MULTILINE)
            discovered = int(plan.group(1)) if plan else 0
            passed_count = len(re.findall(r"^ok\s+\d+\s", out, re.MULTILINE))

        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "perl test_enigma.py (Crypt::Enigma API, 18 assertions)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # Upstream suite evidence (parsed from the real `make test` run).
        self._emit_upstream_result(dep)

        if not marker["passed"]:
            raise ConanException(
                f"test_package failed: {passed_count}/{discovered} assertions passed"
            )
