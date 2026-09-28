#!/usr/bin/env python3
"""Conan test_package for libblzf 3.6.1 — Conan L1 consumer test.

Builds test_lzf.c against the packaged liblzf.a via CMake+CTest (5 API
cases) and registers the packaged bin/lzf CLI script as a 6th ctest test,
then runs the whole suite with ctest. Result counting follows the HMBS
machine-evidence rule: discovered comes from `ctest -N`, per-test
Passed/Failed comes from `Test #N ... Passed|Failed` lines in the
ctest output (prefix-optional, trailing time allowed), cross-checked
against the native `Test Passed./Failed.` verdict lines in
Testing/Temporary/LastTest.log. The stdout summary line is only a
soft check (verified when present, warned when absent) because it is
cosmetic and varies by CTest version/colour. The two deterministic
sources must agree; any mismatch emits an honest
failed marker (with reason) instead of patched-up numbers. No stdout
substring arithmetic, no returncode-based fixups.

Also (re-)emits HMBS_UPSTREAM_TEST_RESULT status=no_tests every run: the
liblzf 3.6 tarball contains no test suite (audited, see MANIFEST.yml), so
there is no upstream result to report.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

# Ctest per-test result line in `ctest --output-on-failure` stdout, e.g.
#   1/6 Test #1: api:roundtrip_text ............   Passed    0.01 sec
# The N/M prefix is optional (some cmake versions omit it) and a time
# suffix always follows the verdict, so neither may be anchored.
TEST_LINE_RE = re.compile(r"Test\s+#(\d+):\s+(\S+).*?\b(Passed|\*\*\*Failed|\*\*\*Timeout|Failed|Timeout)\b")
# Native per-test verdict line at the end of each section in
# Testing/Temporary/LastTest.log, e.g.  "Test Passed." / "Test Failed."
# (LastTest.log does NOT repeat the `Test #N ...` summary lines, so the
# stdout regex can never match it; count its own verdict lines instead.
# One verdict line per test section: single deterministic source, no
# substring arithmetic, no returncode fixups.)
LASTTEST_VERDICT_RE = re.compile(r"^\s*Test\s+(Passed|Failed|Timeout)\.\s*$")
# ctest -N registration line, e.g.   Test #1: api:roundtrip_text
# NOTE: findall() runs on the whole multi-line output, so MULTILINE is
# required for ^/$ to match per line (without it only Total Tests at
# end-of-string matched, yielding "0 Test # lines vs Total Tests: 6").
REGISTER_RE = re.compile(r"^\s*Test\s+#(\d+):\s+(\S+)\s*$", re.MULTILINE)
TOTAL_RE = re.compile(r"Total\s+Tests:\s+(\d+)\s*$", re.MULTILINE)
SUMMARY_RE = re.compile(r"(\d+)% tests passed,\s*(\d+) tests failed out of (\d+)\s*$")

UPSTREAM_NO_TESTS_REASON = (
    "liblzf 3.6 upstream has no test suite: 18-entry tarball "
    "(lzf.h/lzfP.h/lzf_c.c/lzf_d.c/lzf.c crc32.h configure.ac/configure/Makefile.in "
    "cs/CLZF.cs + docs), no tests/ or test/ directory, no *test* source file, "
    "no TESTS/check_PROGRAMS variables, Makefile.in targets are only "
    "all/clean/lzf/liblzf.a/install/dist/bench (no check/test target)"
)


class LiblzfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        from conan.tools.cmake import CMakeDeps, CMakeToolchain
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _resolve_compiler(self, conf_key, names):
        # bwm/0.6.3 + cubelib/4.9.1 precedent: the repo profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang
        # which is missing on some HMBS hosts (conftest rc=127, CMake
        # "CMAKE_C_COMPILER ... broken"). Keep the profile value when the
        # file exists (CI unchanged); otherwise fall back to PATH. Pure
        # isfile probing per R49, no X_OK probing.
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        configured = None
        try:
            configured = conf.get(conf_key)
        except Exception:
            configured = None
        if configured:
            first = str(configured).split()[0].strip("\"'")
            try:
                if first and os.path.isfile(first):
                    self.output.info(
                        f"libblzf test_package keeps configured {conf_key}={configured}")
                    return str(configured).strip()
            except OSError:
                pass
            self.output.info(
                f"libblzf test_package configured {conf_key}={configured} missing, PATH fallback")
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info(f"libblzf test_package {conf_key} PATH fallback: {found}")
                return found
        self.output.info(f"libblzf test_package {conf_key} bare fallback: {names[0]}")
        return names[0]

    def _scrub_toolchain_stale_compilers(self, cc, cxx):
        # cubelib/4.9.1 precedent: CMakeToolchain bakes the stale profile
        # compiler path into conan_toolchain.cmake; when that file is
        # missing on-device, replace it with the resolved fallback so
        # cmake.configure picks a working compiler. No-op on CI where the
        # profile path exists.
        try:
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return
        try:
            if not (toolchain and os.path.isfile(toolchain)):
                return
            with open(toolchain, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return
        rewrote = False
        for stale, good in (("/data/service/hnp/bin/clang++", cxx),
                            ("/data/service/hnp/bin/clang", cc)):
            if stale in content:
                try:
                    missing = not os.path.isfile(stale)
                except OSError:
                    missing = True
                if missing and good and good != stale:
                    content = content.replace(stale, good)
                    rewrote = True
                    self.output.info(f"libblzf test_package scrubbed stale {stale} -> {good}")
        if rewrote:
            try:
                with open(toolchain, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        # R34/L1e: prove the test really uses the packaged artefacts. If the
        # package folder is moved away (CI destructive reverse validation),
        # these checks fail instead of silently falling back to system files.
        for inc in dep.cpp_info.includedirs:
            if not os.path.isdir(inc):
                raise ConanException(f"libblzf package include dir missing: {inc}")
        if not os.path.isdir(dep.cpp_info.libdirs[0]):
            raise ConanException(f"libblzf package lib dir missing: {dep.cpp_info.libdirs[0]}")
        lzf_bin = os.path.join(pkg, "bin", "lzf")
        if not os.path.isfile(lzf_bin):
            raise ConanException(f"libblzf package CLI missing: {lzf_bin}")
        self._ensure_writable_tmp()
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        self._scrub_toolchain_stale_compilers(cc, cxx)
        self.output.info(f"libblzf test_package CMAKE_C_COMPILER={cc} CMAKE_CXX_COMPILER={cxx}")
        cmake = CMake(self)
        cmake.configure(variables={"LZF_BIN": lzf_bin, "TEST_SH": self._usable_shell(),
                                   "CMAKE_C_COMPILER": cc, "CMAKE_CXX_COMPILER": cxx})
        # Serial consumer build (xmlsec/oclgrind precedent): default
        # cmake.build() fans out to all cores; under true-device fork/OOM
        # pressure (/bin/sh: Out of memory, can't fork) cap peak RSS with -j1.
        # No test-logic change; counting stays ctest-log triple-check.
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime tests skipped")
            return
        # Writable TMPDIR first: the CLI script probes TMPDIR itself, but the
        # ctest working dir and LastTest.log also live under it.
        self._ensure_writable_tmp()
        ctest = shutil.which("ctest") or "ctest"
        test_dir = self.build_folder

        # L0d/PF3: real self.run execution in test() (discovery listing;
        # the measured suite run below uses subprocess for output capture).
        self.run(f"{ctest} -N", cwd=test_dir, env="conanrun")
        discovered = self._ctest_discovered(ctest, test_dir)
        proc = self._run_ctest(ctest, test_dir)
        self.output.info("ctest run output tail:\n" + (proc.stdout or "")[-6000:])
        passed, failed, names = self._parse_test_lines(proc.stdout, "ctest stdout")
        self._cross_check_last_test_log(test_dir, discovered, passed, failed)
        self._cross_check_summary(proc.stdout, discovered, failed)

        executed = passed + failed
        suite_ok = (
            proc.returncode == 0
            and executed == discovered
            and failed == 0
            and discovered > 0
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
        # Upstream ships no test suite (audited); report no_tests every run.
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
            raise ConanException(f"libblzf test_package failed: {marker.get('reason')}")

    def _usable_shell(self):
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        return shutil.which("sh") or "/bin/sh"

    def _ensure_writable_tmp(self):
        # OHOS /tmp is read-only: reuse an HMBS-injected writable TMPDIR
        # only after a real touch probe, else fall back to a test-local dir.
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and cand != "/tmp" and os.path.isdir(cand):
                try:
                    probe = os.path.join(cand, ".libblzf_test_wtest")
                    with open(probe, "w") as f:
                        f.write("ok")
                    os.remove(probe)
                    for v in ("TMPDIR", "TMP", "TEMP"):
                        os.environ[v] = cand
                    return cand
                except Exception:
                    continue
        tmpd = os.path.join(self.build_folder, "tmp-test")
        os.makedirs(tmpd, exist_ok=True)
        for v in ("TMPDIR", "TMP", "TEMP"):
            os.environ[v] = tmpd
        return tmpd

    def _run_ctest_list(self, ctest, test_dir):
        return subprocess.run(
            [ctest, "-N"],
            cwd=test_dir,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )

    def _ctest_discovered(self, ctest, test_dir):
        proc = self._run_ctest_list(ctest, test_dir)
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
                f"vs Total Tests: {discovered}"
            )
        if discovered == 0:
            raise ConanException("ctest -N discovered 0 tests, suite is empty")
        return discovered

    def _run_ctest(self, ctest, test_dir):
        return subprocess.run(
            [ctest, "--output-on-failure", "--timeout", "300"],
            cwd=test_dir,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )

    def _parse_test_lines(self, output, origin):
        passed, failed, names = 0, 0, []
        for line in (output or "").splitlines():
            m = TEST_LINE_RE.search(line)
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

    def _parse_lasttest_verdicts(self, content):
        # One verdict line per test section in LastTest.log; single source.
        passed, failed = 0, 0
        for line in (content or "").splitlines():
            m = LASTTEST_VERDICT_RE.match(line)
            if not m:
                continue
            if m.group(1) == "Passed":
                passed += 1
            else:
                failed += 1
        self.output.info(f"LastTest.log: verdicts passed={passed} failed={failed}")
        return passed, failed

    def _find_lasttest_log(self, test_dir):
        # cmake_layout nests the real build dir; prefer the canonical path
        # but fall back to a shallow walk so a moved log is found instead
        # of failing (or reading a stale empty file) with no evidence.
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

    def _cross_check_last_test_log(self, test_dir, discovered, passed, failed):
        log, searched = self._find_lasttest_log(test_dir)
        if not log:
            raise ConanException(
                f"LastTest.log not found or empty; searched: {searched}")
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        self.output.info(f"LastTest.log in use: {log} (size {len(content)})")
        self.output.info("LastTest.log tail:\n" + content[-3000:])
        log_passed, log_failed = self._parse_lasttest_verdicts(content)
        if (log_passed, log_failed) != (passed, failed):
            raise ConanException(
                f"LastTest.log disagrees with ctest stdout: "
                f"log passed={log_passed} failed={log_failed} vs "
                f"stdout passed={passed} failed={failed}"
            )
        if passed + failed != discovered:
            raise ConanException(
                f"executed ({passed + failed}) != discovered ({discovered}), "
                "refusing to patch numbers"
            )

    def _cross_check_summary(self, output, discovered, failed):
        # Dual-source is authoritative (ctest -N registration +
        # LastTest.log verdicts, already cross-checked above). The stdout
        # "% tests passed ... out of M" line is cosmetic and varies by
        # CTest version/colour/width, so a missing line must not fail a
        # suite whose two deterministic sources already agree (observed:
        # stdout parsed 6/0 + LastTest.log 6/0 yet hard gate raised
        # "has no summary line"). Verify it when present; warn when absent.
        text = output or ""
        # Strip ANSI colour escapes before matching (ctest may colourise
        # the summary even when piped on some builds).
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
        for line in text.splitlines():
            m = SUMMARY_RE.search(line)
            if m:
                out_of, sum_failed = int(m.group(3)), int(m.group(2))
                if out_of != discovered or sum_failed != failed:
                    raise ConanException(
                        f"ctest summary disagrees: '{line.strip()}' vs "
                        f"discovered={discovered} failed={failed}"
                    )
                return
        self.output.info(
            "ctest summary line absent; dual-source (ctest -N + "
            f"LastTest.log) already agrees: discovered={discovered} "
            f"failed={failed}, continuing without summary gate"
        )
