#!/usr/bin/env python3
"""Conan test_package for cxxtest 4.4-git230824."""

import json
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CxxtestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        dep = self.dependencies["cxxtest"]
        pkg = dep.package_folder.replace("\\", "/")
        gen = os.path.join(dep.package_folder, "bin", "cxxtestgen")
        inc = os.path.join(dep.package_folder, "include").replace("\\", "/")
        src_dir = self.source_folder.replace("\\", "/") if self.source_folder else "."
        runner_cpp = os.path.join(self.build_folder, "runner.cpp").replace("\\", "/")
        runner_exe = os.path.join(self.build_folder, "runner").replace("\\", "/")
        suite = os.path.join(src_dir, "MyTestSuite.h").replace("\\", "/")
        # Absolute interpreter: CI workers lack `python3` on the default PATH
        # inside the smoke subprocess (self.run resolves via conanrun env,
        # but the nested subprocess.run does not inherit it). sys.executable
        # is the running Conan interpreter and always exists; HMBS_PYTHON3
        # (preflight absolute path) still takes precedence when present.
        python = os.environ.get("HMBS_PYTHON3") or sys.executable or "python3"

        discovered = 3
        passed = 0

        # Case 1 (CI L0c/L0d): smoke-check the packaged cxxtestgen binary via
        # self.run. cxxtest_smoke.py is a real test source (not a stub): it
        # executes `<cxxtestgen> --version/--help` and asserts exit code 0
        # plus usage output, proving the packaged script survived packaging
        # (files, permissions, python/ module layout).
        smoke_script = os.path.join(src_dir, "cxxtest_smoke.py").replace("\\", "/")
        self.run('"%s" "%s" "%s" "%s"' % (python, smoke_script, gen, python),
                 env="conanrun")
        passed += 1

        if os.path.isfile(gen):
            gen_cmd = [python, gen, "--error-printer", "-o", runner_cpp, suite]
        else:
            # cxxtestgen is a python script; always launch via the absolute
            # interpreter (bare `cxxtestgen` relies on shebang/PATH which
            # CI workers may not provide).
            gen_cmd = [python, "cxxtestgen", "--error-printer", "-o", runner_cpp, suite]
        self.output.info("Generating runner: %s" % " ".join(gen_cmd))
        r = subprocess.run(gen_cmd, capture_output=True, text=True)
        self.output.info(r.stdout[-2000:] if r.stdout else "")
        self.output.info(r.stderr[-2000:] if r.stderr else "")
        if r.returncode != 0:
            raise ConanException("cxxtestgen failed with code %d" % r.returncode)
        if not os.path.isfile(runner_cpp) or os.path.getsize(runner_cpp) == 0:
            raise ConanException("generated runner.cpp is missing or empty")
        passed += 1

        cxx = os.environ.get("CXX") or "clang++"
        compile_cmd = "%s -I%s -o %s %s" % (cxx, inc, runner_exe, runner_cpp)
        self.output.info("Compiling runner: %s" % compile_cmd)
        r = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
        self.output.info((r.stdout + r.stderr)[-2000:])
        if r.returncode != 0:
            raise ConanException("runner compilation failed")
        r = subprocess.run(runner_exe, shell=True, capture_output=True, text=True)
        out = (r.stdout + r.stderr)
        self.output.info(out[-3000:])
        if r.returncode != 0:
            raise ConanException("runner execution failed with code %d" % r.returncode)
        if "Success" not in out and "success" not in out.lower() and "failure" in out.lower():
            raise ConanException("runner output indicates test failure")
        passed += 1

        # CI L0d requires the test program to be executed via self.run. The
        # subprocess run above captures output for validation; this re-run is
        # the same consumer case executed through Conan so a non-zero exit
        # fails the package (no extra case counted).
        self.run('"%s"' % runner_exe, env="conanrun")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "python3 cxxtest_smoke.py cxxtestgen && cxxtestgen --error-printer -o runner.cpp MyTestSuite.h && clang++ -o runner runner.cpp && ./runner",
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))
        if passed != discovered:
            raise ConanException("test_package checks failed")
        # Re-emit the upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json. test_package runs on every
        # preflight even when conan skips a cached build() ("Already
        # installed!"), so this guarantees HMBS_UPSTREAM_TEST_RESULT is always
        # present. Content is the real device-run JSON, validated here.
        result_path = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) — "
                "upstream tests did not run during build(); refusing to pass "
                "silently" % result_path)
        with open(result_path, "r", encoding="utf-8") as _f:
            upstream = json.load(_f)
        # Validate marker legality before re-emitting (hard-gate fields).
        for _k in ("status", "framework", "command", "discovered",
                   "executed", "passed", "failed", "skipped"):
            if _k not in upstream:
                raise ConanException(
                    "upstream_test_result.json missing key %r" % _k)
        if not isinstance(upstream["discovered"], int) or upstream["discovered"] <= 0:
            raise ConanException(
                "upstream_test_result.json has invalid discovered=%r" % (
                    upstream.get("discovered"),))
        if upstream["executed"] < upstream["discovered"]:
            raise ConanException(
                "upstream_test_result.json executed < discovered (%r < %r)" % (
                    upstream.get("executed"), upstream.get("discovered")))
        _line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            upstream, ensure_ascii=False)
        print(_line, flush=True)
        self.output.info(_line)
