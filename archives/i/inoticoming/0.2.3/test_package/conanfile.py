#!/usr/bin/env python3
"""Conan test_package — inoticoming 0.2.3 (consumer + OHOS-specific tests).

inoticoming is a CLI daemon, so there is nothing to link: the tests drive
the installed binary on the target.  Up to two independent scripts are run
and both must pass:

  * test_inoticoming.py       — consumer/functional test (6 cases):
    --version, --help, IN_CLOSE_WRITE dispatch, IN_MOVED_TO dispatch,
    --suffix filtering and SIGTERM shutdown.  Runs on any OS the package
    supports.
  * test_ohos_inoticoming.py  — OHOS 专项测试 (6 cases, OHOS-only
    addition): OHOS ELF/loader identity, inotify kernel ABI on
    HarmonyOS, --initialsearch over the OHOS filesystem (readdir
    d_type), --chdir + --pid-file semantics, and daemonized --logfile
    operation without syslogd.  Launched only when the test target is
    OHOS (its first case asserts PT_INTERP=/lib/ld-musl-aarch64.so.1);
    on other targets it is reported as skipped instead of failing.

Upstream 0.2.3 ships no test suite (audit in test_package/MANIFEST.yml):
`make check` exists but registers zero TESTS, therefore
HMBS_UPSTREAM_TEST_RESULT is reported as status=no_tests.
"""

import json
import os
import re
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class InoticomingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _checks(self):
        """(label, script, expected case count) for the current target."""
        checks = [("consumer", "test_inoticoming.py", 6)]
        if str(self.settings.os) == "OHOS":
            checks.append(("ohos", "test_ohos_inoticoming.py", 6))
        return checks

    def _run_script(self, label, script_name, expected, binary, tmpdir):
        """Run one test script, log it, and return the parsed result dict."""
        script = os.path.join(self.recipe_folder, script_name)
        if not os.path.isfile(script):
            raise ConanException("test script missing: %s" % script)
        workdir = os.path.join(tmpdir, "inoticoming-%s-test" % label)
        os.makedirs(workdir, exist_ok=True)
        log = os.path.join(workdir, "%s.log" % label)
        python = sys.executable or "python3"
        command = '"%s" "%s" "%s" "%s" > "%s" 2>&1' % (
            python, script, binary, workdir, log
        )
        self.output.info("running: %s" % command)
        retcode = self.run(command, env="conanrun", cwd=workdir, ignore_errors=True)

        output = ""
        if os.path.isfile(log):
            with open(log, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
        self.output.info("%s output:\n%s"
                         % (script_name, "\n".join(output.splitlines()[-30:])))

        match = re.search(r"RESULT: (\d+) passed, (\d+) failed", output)
        if not match:
            raise ConanException(
                "%s produced no RESULT line (rc=%s, tail=%r)"
                % (script_name, retcode, output[-300:])
            )
        passed, failed = int(match.group(1)), int(match.group(2))
        return {
            "script": script_name,
            "retcode": retcode,
            "passed": passed,
            "failed": failed,
            "discovered": passed + failed,
            "expected": expected,
        }

    def test(self):
        if not can_run(self):
            raise ConanException(
                "inoticoming test_package must run on the build target "
                "(os=%s arch=%s)" % (self.settings.os, self.settings.arch)
            )

        package_folder = self.dependencies["inoticoming"].package_folder
        binary = os.path.join(package_folder, "bin", "inoticoming")
        if not os.path.isfile(binary):
            raise ConanException("binary not found in package: %s" % binary)

        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )

        checks = self._checks()
        results = [
            self._run_script(label, script_name, expected, binary, tmpdir)
            for label, script_name, expected in checks
        ]
        ohos_ran = any(label == "ohos" for label, _, _ in checks)
        if not ohos_ran:
            self.output.info(
                "OHOS-specific test skipped: target os=%s (it asserts the "
                "OHOS musl loader in case 1)" % self.settings.os
            )

        marker = {
            "executed": True,
            "passed": all(r["failed"] == 0 and r["retcode"] == 0
                          and r["discovered"] == r["expected"] for r in results),
            "command": " + ".join(
                "python3 %s <bin> <workdir>" % r["script"] for r in results
            ),
            "discovered": sum(r["discovered"] for r in results),
            "passedCount": sum(r["passed"] for r in results),
            "ohos_specific": ("executed" if ohos_ran
                              else "skipped (target os=%s)" % self.settings.os),
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )

        failures = [
            "%s: rc=%s, %d passed, %d failed, discovered %d (expected %d)"
            % (r["script"], r["retcode"], r["passed"], r["failed"],
               r["discovered"], r["expected"])
            for r in results
            if r["failed"] or r["retcode"] != 0 or r["discovered"] != r["expected"]
        ]
        if failures:
            raise ConanException("inoticoming test_package failed: "
                                 + "; ".join(failures))

        upstream_marker = {
            "status": "no_tests",
            "framework": "automake-make-check",
            "command": "make check (upstream registers no TESTS)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "inoticoming 0.2.3 上游无任何测试套件：tarball 26 个条目中"
                "无 tests/ 或 test/ 目录、无 *test* 源文件；Makefile.am 只定义"
                "bin_PROGRAMS/man_MANS/EXTRA_DIST，没有 TESTS/check_PROGRAMS，"
                "因此 automake 生成的 check 目标不注册任何用例（实测 make check "
                "退出码 0 且无输出，make -n check 只展开编译规则）；"
                "configure.ac 无 AC_CONFIG_TESTDIR，README/INSTALL/ChangeLog "
                "亦无测试入口描述"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("inoticoming consumer tests passed"
                         + (" (+ OHOS-specific tests)" if ohos_ran else ""))
