#!/usr/bin/env python3
"""Conan test_package — detachtty 11.0.0.

detachtty is a pure tool package (bin/detachtty plus bin/attachtty), so
build() does no library linking; test() executes the installed binaries
on the target. Three real cases run in test_detachtty.py:

  1. `detachtty --version` prints "detachtty version 11.0.0".
  2. `attachtty` with no arguments exits non-zero with a usage message.
  3. End-to-end: start `detachtty --no-detach <socket> /bin/sleep 30`,
     wait for the socket file, connect once with
     `attachtty <socket> <text> <timeout>`, require exit 0, then clean up.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount come from the script's
  "RESULT: N passed, M failed" line.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream 11.0.0 ships no
  test suite (audit in test_package/MANIFEST.yml). Re-emitted here because
  the main recipe build() has no upstream test output.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class DetachttyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("detachtty test_package requires can_run on OHOS")

        package_folder = self.dependencies["detachtty"].package_folder
        detachtty = os.path.join(package_folder, "bin", "detachtty")
        attachtty = os.path.join(package_folder, "bin", "attachtty")
        for binary in (detachtty, attachtty):
            if not os.path.isfile(binary):
                raise ConanException("binary not found in package: %s" % binary)

        test_script = os.path.join(self.recipe_folder, "test_detachtty.py")
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        os.makedirs(tmpdir, exist_ok=True)
        logfile = os.path.join(self.build_folder, "test_package.log")
        actual_command = (
            'python3 "%s" "%s" "%s" "%s" > "%s" 2>&1'
            % (test_script, detachtty, attachtty, tmpdir, logfile)
        )
        try:
            self.run(actual_command, env="conanrun", cwd=tmpdir)
        except Exception:
            _out = ""
            if os.path.isfile(logfile):
                with open(logfile, "r", encoding="utf-8", errors="replace") as _h:
                    _out = _h.read()
            self.output.info("test_detachtty.py log (on failure):\n" + "\n".join(_out.splitlines()[-40:]))
            raise

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info(
            "test_detachtty.py log:\n" + "\n".join(out.splitlines()[-40:])
        )

        match = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not match:
            raise ConanException(
                "test_detachtty.py produced no RESULT line — harness broken"
            )
        passed = int(match.group(1))
        failed = int(match.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered == 3 and passed == 3

        marker = {
            "executed": True,
            "passed": ok,
            "command": 'python3 test_detachtty.py "<bin/detachtty>" "<bin/attachtty>"',
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_detachtty.py failed: %d passed, %d failed" % (passed, failed)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest (upstream provides no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "detachtty 11.0.0 上游发布包无任何测试套件：顶层仅 "
                "COPYING/ChangeLog/INSTALL/Makefile/README/attachtty.c/"
                "config.h/copy-stream.c/detachtty.1/detachtty.c/errors.c/"
                "forkpty.c/forkpty.h，无 tests/ 或 test/ 目录、无 *test* "
                "源文件；Makefile 仅 all/clean/install/deb 目标，无 "
                "check/test 目标；README/INSTALL 仅描述构建安装，无测试入口"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("detachtty functional test_package passed")
