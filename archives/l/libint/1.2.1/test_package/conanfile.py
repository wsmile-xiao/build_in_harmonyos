#!/usr/bin/env python3
"""Conan test_package for libint 1.2.1 — Conan L1 消费者测试。

构建单个消费者可执行文件 test_libint（真实调用安装出的 libint.a 的公开 C
API，10 条断言，任一失败非零退出），经 CTest 注册为 1 个用例并整个跑一遍。

计数遵循 HMBS 机器证据硬门禁：discovered 来自 `ctest -N` 的
`Total Tests: N` 与 `Test #N` 逐条注册行（两者必须一致且 >0）；passed/failed
来自 ctest 输出的 `Test #N ... Passed|Failed` 逐条判定行，并交叉核对
`Testing/Temporary/LastTest.log` 的原生 `Test Passed./Failed.` 判定行。两个
确定性来源必须一致；identity（passed+failed==executed、executed<=discovered、
各计数非负）不满足时如实报 failed（带 reason），不做字符串数数/算术修补或
returncode==0 就把 passed 改回 discovered 的猜测修正。

上游 libint 1.2.1 无任何自动化测试（已审计，见 MANIFEST.yml 的
upstream_test_audit），故每次运行都重发 HMBS_UPSTREAM_TEST_RESULT status=no_tests。
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

# ctest -N 注册行：Test #1: libint_consumer
REGISTER_RE = re.compile(r"^\s*Test\s+#(\d+):\s+(\S+)\s*$", re.MULTILINE)
# ctest -N 汇总：Total Tests: N
TOTAL_RE = re.compile(r"Total\s+Tests:\s+(\d+)\s*$", re.MULTILINE)
# ctest --output-on-failure 的逐条判定行：Test #1: libint_consumer ... Passed/Failed
# N/M 前缀可选，判定词后带时间，二者都不要锚定。
VERDICT_LINE_RE = re.compile(
    r"Test\s+#(\d+):\s+(\S+).*?\b(Passed|\*\*\*Failed|\*\*\*Timeout|Failed|Timeout)\b")
# LastTest.log 原生判定行："Test Passed." / "Test Failed." / "Test Timeout."
LASTTEST_VERDICT_RE = re.compile(r"^\s*Test\s+(Passed|Failed|Timeout)\.\s*$")

UPSTREAM_NO_TESTS_REASON = (
    "libint 1.2.1 upstream has no test suite: the release-1-2-1 tag tarball "
    "(== Debian libint_1.2.1.orig.tar.gz) contains only src/{bin,lib} generator + "
    "library sources, doc/, configure.ac / Makefile / CMakeLists.txt; no tests/ "
    "dir, no *test* source, no TESTS/check_PROGRAMS in configure.ac, no "
    "check/test target in Makefile, no enable_testing()/add_test()/CTest "
    "registration in CMakeLists (full audit in test_package/MANIFEST.yml)"
)


class LibintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime tests skipped")
            return
        test_dir = self.build_folder
        ctest = shutil.which("ctest") or "ctest"

        # PF3/L0d：真实 self.run 执行（发现列表；实测套件运行用 subprocess 捕获输出）
        self.run(f"{ctest} -N", cwd=test_dir, env="conanrun")
        discovered = self._ctest_discovered(ctest, test_dir)
        proc = self._run_ctest(ctest, test_dir)
        self.output.info("ctest run output tail:\n" + (proc.stdout or "")[-6000:])
        passed, failed, names = self._parse_verdicts(proc.stdout, "ctest stdout")
        self._cross_check_lasttest_log(test_dir, discovered, passed, failed)

        executed = passed + failed
        suite_ok = (
            proc.returncode == 0
            and executed == discovered > 0
            and failed == 0
        )
        command = f"{ctest} --output-on-failure --timeout 300"
        marker = {
            "executed": True,
            "passed": suite_ok,
            "command": command,
            "discovered": discovered,
            "passedCount": passed,
        }
        if not suite_ok:
            marker["reason"] = (
                f"ctest rc={proc.returncode} discovered={discovered} "
                f"executed={executed} passed={passed} failed={failed} "
                f"cases={names}"
            )
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)

        # 上游无测试套件（已审计）：如实上报 no_tests。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "make (no check/test target upstream)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": UPSTREAM_NO_TESTS_REASON,
        }
        umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker)
        print(umsg, flush=True)
        self.output.info(umsg)

        if not suite_ok:
            raise ConanException(f"libint test_package failed: {marker.get('reason')}")

    # ── 计数辅助（单一确定性来源 + 交叉核对） ────────────────────────────

    def _ctest_discovered(self, ctest, test_dir):
        proc = subprocess.run([ctest, "-N"], cwd=test_dir, env=dict(os.environ),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=300)
        output = proc.stdout or ""
        self.output.info("ctest -N output:\n" + output[-2000:])
        if proc.returncode != 0:
            raise ConanException(f"ctest -N failed rc={proc.returncode}:\n{output[-2000:]}")
        registered = REGISTER_RE.findall(output)
        totals = TOTAL_RE.findall(output)
        if not totals:
            raise ConanException(f"ctest -N has no 'Total Tests' line:\n{output[-2000:]}")
        discovered = int(totals[-1])
        if len(registered) != discovered:
            raise ConanException(
                f"ctest -N count mismatch: {len(registered)} Test # lines "
                f"vs Total Tests: {discovered}")
        if discovered == 0:
            raise ConanException("ctest -N discovered 0 tests, suite is empty")
        return discovered

    def _run_ctest(self, ctest, test_dir):
        return subprocess.run([ctest, "--output-on-failure", "--timeout", "300"],
                              cwd=test_dir, env=dict(os.environ),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=600)

    def _parse_verdicts(self, output, origin):
        passed, failed, names = 0, 0, []
        for line in (output or "").splitlines():
            m = VERDICT_LINE_RE.search(line)
            if not m:
                continue
            verdict = m.group(3).replace("*", "")
            names.append(f"#{m.group(1)}:{m.group(2)}={verdict}")
            if verdict == "Passed":
                passed += 1
            else:
                failed += 1
        self.output.info(f"{origin}: parsed passed={passed} failed={failed} cases={names}")
        return passed, failed, names

    def _find_lasttest_log(self, test_dir):
        candidates = [os.path.join(test_dir, "Testing", "Temporary", "LastTest.log")]
        try:
            for root, dirs, files in os.walk(test_dir):
                if "LastTest.log" in files:
                    p = os.path.join(root, "LastTest.log")
                    if p not in candidates:
                        candidates.append(p)
                if root.count(os.sep) - test_dir.count(os.sep) > 6:
                    dirs[:] = []
        except Exception:
            pass
        searched = []
        for p in candidates:
            searched.append(p)
            try:
                if os.path.isfile(p) and os.path.getsize(p) > 0:
                    return p, searched
            except OSError:
                continue
        return "", searched

    def _cross_check_lasttest_log(self, test_dir, discovered, passed, failed):
        log, searched = self._find_lasttest_log(test_dir)
        if not log:
            raise ConanException(f"LastTest.log not found or empty; searched: {searched}")
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        self.output.info(f"LastTest.log in use: {log} (size {len(content)})")
        log_passed, log_failed = 0, 0
        for line in content.splitlines():
            m = LASTTEST_VERDICT_RE.match(line)
            if not m:
                continue
            if m.group(1) == "Passed":
                log_passed += 1
            else:
                log_failed += 1
        self.output.info(f"LastTest.log: verdicts passed={log_passed} failed={log_failed}")
        if (log_passed, log_failed) != (passed, failed):
            raise ConanException(
                f"LastTest.log disagrees with ctest stdout: "
                f"log passed={log_passed} failed={log_failed} vs "
                f"stdout passed={passed} failed={failed}")
        if passed + failed != discovered:
            raise ConanException(
                f"executed ({passed + failed}) != discovered ({discovered}), "
                "refusing to patch numbers")
        if failed < 0 or passed < 0 or discovered < 0:
            raise ConanException("negative count in test result, single-source broken")
