#!/usr/bin/env python3
"""Conan test_package — clock-setup 0.168 (set-date-epoch tool).

clock-setup is a tool package (bin/set-date-epoch), so build() does no
link check; test() really executes the installed binary via
test_set_date_epoch.sh (R34: 6 content-level cases, anti-stub string
checks plus silent-success behavior checks).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount from the script's
  real RESULT line.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. The upstream tarball has
  no test suite (no tests/ dir, Makefile has no check/test target;
  debian/rules only runs `sh -n` packaging lint). Re-emitted here every
  round because the main build output is skipped on package-cache hits.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class ClockSetupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        # Tool package: no library to link; functional checks run in test().
        pass

    def test(self):
        pkg_bin = os.path.join(
            self.dependencies["clock-setup"].package_folder,
            "bin", "set-date-epoch")
        if not os.path.isfile(pkg_bin):
            raise ConanException(
                "set-date-epoch binary not found in package: %s" % pkg_bin)

        # Do not hard-code the HNP bash path: prefer hmbs/profile injected
        # CONFIG_SHELL/SHELL, fall back to /bin/sh.
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")

        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_set_date_epoch.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("SET_DATE_EPOCH_BIN", pkg_bin)
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
        self.output.info("test_set_date_epoch.sh log:\n"
                         + "\n".join(out.splitlines()[-16:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_set_date_epoch.sh produced no RESULT line — harness broken")
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
                "test_set_date_epoch.sh failed: %d/%d cases failed"
                % (failed, discovered))

        # Upstream test marker: clock-setup 0.168 ships no test suite.
        # Audit basis (see test_package/MANIFEST.yml upstream_test_audit):
        # no tests/ or test/ directory; Makefile targets are only
        # set-date-epoch/build/clean; debian/rules override_dh_auto_test
        # runs `sh -n` syntax lint only (packaging lint, zero test cases).
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make build (upstream Makefile provides no check/test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "clock-setup 0.168 上游无任何测试套件：源码树无 tests/ 或 test/ 目录；"
                "Makefile 目标仅 set-date-epoch/build/clean，无 check/test 目标；"
                "debian/rules 的 override_dh_auto_test 仅对 2 个 shell 脚本做 sh -n "
                "语法检查（打包期 lint，0 个测试用例）；debian/control 的 "
                "Build-Depends 仅 debhelper-compat 与 po-debconf，无测试框架依赖"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("clock-setup functional test_package passed")
