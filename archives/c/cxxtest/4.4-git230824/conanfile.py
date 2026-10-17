#!/usr/bin/env python3
"""Conan recipe for cxxtest 4.4-git230824 (custom, header-only + cxxtestgen)."""

import json
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.layout import basic_layout


class CxxtestConan(ConanFile):
    name = "cxxtest"
    version = "4.4-git230824"
    description = "C++ unit testing framework similar to JUnit, CppUnit and xUnit"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/CxxTest/cxxtest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "testing", "unit-test", "header-only", "cxxtestgen"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    # TestClang.test_int64 requires MSVC/Borland `__int64` (test/int64.cpp
    # probes `__int64 ll = 0;`, test/Int64.h is consumed with
    # `--longlong=__int64`). clang on OHOS/Linux cannot compile that probe,
    # so upstream correctly calls skipTest("64-bit integers are not supported
    # by this compiler"). The HMBS hard gate rejects any skipped>0, so this
    # single Windows-only case is excluded via explicit unittest selectors
    # (not counted in discovered, not claimed as passed) following the
    # python3-cairo 1.29.1 precedent (excluded_cases + total_upstream_cases).
    _EXCLUDED_UPSTREAM_CASES = [
        "TestClang.test_int64",
    ]
    _EXCLUDED_REASON = (
        "TestClang.test_int64 needs MSVC/Borland __int64 "
        "(test/int64.cpp: '__int64 ll = 0;'); clang++ on HarmonyOS aarch64 "
        "cannot compile that probe, upstream skips with "
        "'64-bit integers are not supported by this compiler'. "
        "Windows-only capability, excluded and reported here instead of "
        "counted as passed (HMBS hard gate rejects skipped)."
    )

    def _discover_clang_tests(self, test_script):
        try:
            with open(test_script, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            return []
        # Only match real definitions at line start (optional indent + def).
        # A naive `def (test_\w+)` also matches the commented-out
        # `    # def test_factor(self):` and would select a non-existent
        # TestClang.test_factor, which unittest reports as a loader ERROR
        # (AttributeError, FAILED errors=1). Anchor to line start to skip
        # comments.
        names = re.findall(r"^\s*def (test_\w+)", text, flags=re.M)
        seen = set()
        uniq = []
        for n in names:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        return uniq

    def _run_upstream_tests(self):
        test_dir = os.path.join(self.source_folder, "test")
        test_script = os.path.join(test_dir, "test_cxxtest.py")
        if not os.path.isfile(test_script):
            raise ConanException("upstream test entry test/test_cxxtest.py not found")
        # Prefer the HMBS absolute interpreter on preflight; fall back to the
        # running Conan interpreter (always exists) instead of bare "python3",
        # which CI workers may not have on the default PATH.
        python = os.environ.get("HMBS_PYTHON3") or sys.executable or "python3"
        all_tests = self._discover_clang_tests(test_script)
        excluded_short = {c.split(".")[-1] for c in self._EXCLUDED_UPSTREAM_CASES}
        selected = [n for n in all_tests if n not in excluded_short]
        if not selected:
            raise ConanException("no upstream TestClang cases selected after exclusion")
        # Explicit selectors keep the run honest: unittest reports Ran N for
        # exactly the N selected cases; the excluded Windows-only case never
        # runs and is reported in excluded_cases below (not as passed).
        cmd = [python, test_script] + ["TestClang.%s" % n for n in selected]
        self.output.info("Running upstream CxxTest suite: %s (selected %d/%d, excluded %s)" % (
            test_script, len(selected), len(all_tests), ",".join(self._EXCLUDED_UPSTREAM_CASES)))
        self.output.info("Excluded reason: %s" % self._EXCLUDED_REASON)
        # Upstream test_normal_sympath/test_normal_relpath must run from the
        # tests folder: they use process-cwd-relative paths ('../.git',
        # '../test_relpath', 'test_sympath') while generated commands use
        # absolute currdir. Running from source root splits the two views and
        # breaks cxxtestgen output paths. Conan tarball extracts have no .git,
        # so provide an ephemeral placeholder to satisfy the upstream guard
        # without touching upstream test logic.
        git_marker = os.path.join(self.source_folder, ".git")
        created_git_marker = False
        if not os.path.exists(git_marker):
            try:
                os.mkdir(git_marker)
                created_git_marker = True
            except Exception as e:
                self.output.warning("could not create ephemeral .git marker: %s" % e)
        try:
            proc = subprocess.run(
                cmd,
                cwd=test_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=3600,
            )
        finally:
            if created_git_marker:
                try:
                    os.rmdir(git_marker)
                except Exception:
                    pass
        output = proc.stdout or ""
        for line in output.splitlines()[-40:]:
            self.output.info("[upstream] %s" % line)
        ran = 0
        failures = 0
        errors = 0
        skipped = 0
        m = re.search(r"Ran (\d+) tests?", output)
        if m:
            ran = int(m.group(1))
        m = re.search(r"OK(?: \(skipped=(\d+)\))?", output)
        ok = m is not None
        if m and m.group(1):
            skipped = int(m.group(1))
        m = re.search(r"FAILED \((.*?)\)", output)
        if m:
            detail = m.group(1)
            mf = re.search(r"failures=(\d+)", detail)
            me = re.search(r"errors=(\d+)", detail)
            ms = re.search(r"skipped=(\d+)", detail)
            failures = int(mf.group(1)) if mf else 0
            errors = int(me.group(1)) if me else 0
            skipped = int(ms.group(1)) if ms else skipped
            ok = False
        passed = ran - failures - errors - skipped if ran else 0
        if passed < 0:
            passed = 0
        # Honesty guard: unittest must have run exactly the selected cases.
        # If upstream adds/removes tests, `selected` adapts via discovery, but
        # a mismatch here means the harness did not run what we claimed.
        expected = len(selected)
        total_upstream = len(all_tests)
        if ran != expected:
            self.output.warning(
                "upstream Ran count mismatch: got %d, selected %d (total %d)" % (
                    ran, expected, total_upstream))
        status = "passed" if (proc.returncode == 0 and ok and ran > 0 and ran == expected) else "failed"
        # HMBS hard gate rejects skipped>0: the excluded Windows-only case is
        # reported here (not in discovered/executed/passed), mirroring the
        # python3-cairo 1.29.1 excluded_cases pattern.
        full_command = " ".join(cmd)
        # Marker command is the reproducible relative form with all selectors;
        # the absolute full command is logged above for audit.
        selectors = " ".join("TestClang.%s" % n for n in selected)
        relative_command = "python3 test/test_cxxtest.py %s" % selectors
        self.output.info("Full upstream command: %s" % full_command)
        marker = {
            "status": status,
            "framework": "unittest",
            "command": relative_command,
            "discovered": ran,
            "executed": ran,
            "passed": passed,
            "failed": failures + errors,
            "skipped": skipped,
            "excluded_cases": self._EXCLUDED_UPSTREAM_CASES,
            "excluded_count": len(self._EXCLUDED_UPSTREAM_CASES),
            "total_upstream_cases": total_upstream,
            "reason": self._EXCLUDED_REASON,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker), flush=True)
        # Dual-channel: Conan may route print vs self.output differently
        # across versions/sinks; emit the identical line via both so the
        # HMBS log parser always sees it.
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker))
        sys.stdout.flush()
        # Persist the real device-run result so test_package can re-emit the
        # identical marker on EVERY run. `conan create` skips build()
        # entirely on a cached binary ("Already installed!"), which previously
        # left the gate without upstream evidence (incomplete).
        try:
            result_path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as _f:
                json.dump(marker, _f, ensure_ascii=False)
            self.output.info("persisted upstream test result to %s" % result_path)
        except Exception as _e:
            raise ConanException("failed to persist upstream_test_result.json: %s" % _e)
        if skipped > 0:
            raise ConanException(
                "upstream CxxTest suite has %d SKIPPED cases; HMBS hard gate "
                "rejects skipped — fix or exclude with a documented reason "
                "(ran=%d passed=%d failed=%d)" % (
                    skipped, ran, passed, failures + errors)
            )
        if status != "passed":
            raise ConanException(
                "upstream CxxTest suite failed (ran=%d/%d passed=%d failed=%d skipped=%d)" % (
                    ran, expected, passed, failures + errors, skipped)
            )

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "cxxtest"),
             dst=os.path.join(self.package_folder, "include", "cxxtest"))
        # Generated runner.cpp does `#include <cxxtest/Root.cpp>` which in
        # turn pulls the other cxxtest/*.cpp implementation fragments, so the
        # .cpp files must be shipped alongside the headers (header-only usage
        # compiles them via #include, no separate library build needed).
        copy(self, "*.cpp", src=os.path.join(self.source_folder, "cxxtest"),
             dst=os.path.join(self.package_folder, "include", "cxxtest"))
        copy(self, "cxxtestgen", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(self.source_folder, "python"),
             dst=os.path.join(self.package_folder, "python"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        gen = os.path.join(self.package_folder, "bin", "cxxtestgen")
        if os.path.isfile(gen):
            try:
                os.chmod(gen, 0o755)
            except Exception:
                pass
        # Ship the persisted upstream result so test_package can re-emit the
        # identical HMBS_UPSTREAM_TEST_RESULT marker even when conan skips
        # build() on a cached binary.
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json",
                 self.build_folder, res_dir, keep_path=False)
        else:
            self.output.warning("upstream_test_result.json not found in build "
                                "folder; package will lack upstream evidence")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
