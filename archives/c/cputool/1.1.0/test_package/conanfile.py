#!/usr/bin/env python3
"""Conan test_package — cputool 1.1.0 (CPU usage management CLI tool).

cputool is a tool-type package (bin/cputool), with no library to link,
so build() does no CMake linking; test() runs test_cputool.sh against
the installed binary for 5 content-level functional checks (-V version,
--help usage, no-arg error, invalid -c/-l rejection), satisfying L0d
(test() uses self.run) and R34 (real invocation of the tested binary).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount from the script's
  real count (RESULT: N passed, M failed line).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream 1.1.0 ships no
  test suite (no tests/ dir, no meson test() targets; audit in
  MANIFEST.yml). Re-emitted in every test() run — the main recipe
  build() has no upstream test output, and cache-hit rounds need
  evidence too.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class CputoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        # Tool-type package needs no link check; functional checks run in
        # test() against bin/cputool.
        pass

    def test(self):
        cputool = os.path.join(
            self.dependencies["cputool"].package_folder,
            "bin", "cputool")
        if not os.path.isfile(cputool):
            raise ConanException(
                "cputool binary not found in package: %s" % cputool)

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_cputool.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("CPUTOOL_BIN", cputool)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)

        inner = '"%s" "%s" > "%s" 2>&1' % (shell, test_script, logfile)
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
        self.output.info("test_cputool.sh log:\n"
                         + "\n".join(out.splitlines()[-16:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_cputool.sh produced no RESULT line — harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s %s" % (shell, test_script),
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise RuntimeError(
                "test_cputool.sh failed: %d/%d cases failed"
                % (failed, discovered))

        # Upstream test marker: cputool 1.1.0 ships no test suite.
        # Audit basis (see test_package/MANIFEST.yml upstream_test_audit):
        # the release tarball has 15 members and no tests/ directory or
        # *test* files; meson.build defines only executable(cputool) with
        # no test() targets; meson_options.txt only carries path/feature
        # options; .gitlab-ci.yml only builds (no test stage).
        upstream_marker = {
            "status": "no_tests",
            "framework": "meson",
            "command": "meson test (upstream defines no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cputool 1.1.0 ships no test suite: "
                "release tarball holds 15 members with no tests/ directory "
                "and no *test* source files; meson.build defines only "
                "executable(cputool) plus docs, with no test() targets; "
                "meson_options.txt carries only path/feature options "
                "(system/runstatedir/docdir/docs); .gitlab-ci.yml runs "
                "meson+ninja+cputool --version with no test stage"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("cputool functional test_package passed")
