#!/usr/bin/env python3
"""Conan test_package — pce 0.2.2 (PC emulator suite, tool package).

pce is a tool package (bin/pce-ibmpc, pce-macplus, pce-rc759 plus four
simulators); there is no library to link, so build() is a no-op and
test() executes test_pce.sh against the installed binaries. Each of the
7 emulators is checked with a version flag (-V for ibmpc/macplus/rc759,
--version fallback for the sim* family) and --help (usage),
for 14 content-level assertions, satisfying L0d and R34.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount from the script's
  RESULT line (real counts, never guessed).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream 0.2.2 ships no
  tests/ directory, no check target and no gtest/ctest/pytest wiring
  (audit in MANIFEST.yml). Re-emitted here because the main recipe
  build() has no upstream test output and cache-hit runs still need
  evidence.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class PceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        bindir = os.path.join(
            self.dependencies["pce"].package_folder, "bin")
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_pce.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)

        inner = '"%s" "%s" "%s" > "%s" 2>&1' % (shell, test_script, bindir, logfile)
        if shutil.which("timeout"):
            cmd = "timeout 90 %s" % inner
        elif os.path.isfile("/data/service/hnp/bin/timeout"):
            cmd = "/data/service/hnp/bin/timeout 90 %s" % inner
        else:
            cmd = inner
        with env_vars.vars(self).apply():
            self.run(cmd, env=None, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_pce.sh log:\n" + "\n".join(out.splitlines()[-30:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException("test_pce.sh produced no RESULT line - harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s test_pce.sh <package>/bin" % shell,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise RuntimeError("test_pce.sh failed: %d/%d cases failed" % (failed, discovered))

        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest (upstream provides no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("pce 0.2.2 upstream ships no test suite: "
                       "tarball has no tests/ or test/ directory and no *test* source file; "
                       "top-level Makefile.in defines no check target; "
                       "configure.in contains no enable_testing/add_test/TEST wiring; "
                       "README/INSTALL describe only ./configure && make && make install"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("pce functional test_package passed")
