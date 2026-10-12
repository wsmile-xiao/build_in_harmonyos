#!/usr/bin/env python3
"""Conan test_package for bs-thread-pool 5.1.0 — consumer verification.

Builds test_bs_thread_pool.cpp against the packaged header and runs it.
Emits HMBS_TEST_PACKAGE_RESULT with counts parsed from the single
deterministic summary line "PASS: X/Y checks passed.".
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BsThreadPoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _probe_ok(self, bash, cmd):
        try:
            proc = subprocess.run(
                [bash, "-c", '"%s" --version' % cmd],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=60)
            self.output.info("cxx probe '%s' rc=%s: %s"
                             % (cmd, proc.returncode, (proc.stdout or "")[-500:]))
            return proc.returncode == 0
        except Exception as exc:
            self.output.info("cxx probe '%s' exception: %s" % (cmd, exc))
            return False

    def _find_working_cxx(self, bash):
        # CMakeToolchain defaults to the profile compiler
        # (/data/service/hnp/bin/clang++), which真机 reports as
        # 'inaccessible or not found'. Probe every source and return the
        # first runnable one instead of trusting the profile blindly.
        import shutil
        candidates = []
        try:
            comp_exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            if isinstance(comp_exes, dict):
                for key in ("cpp", "cxx", "c++", "c"):
                    val = comp_exes.get(key)
                    if val and val not in candidates:
                        candidates.append(val)
        except Exception as exc:
            self.output.info("conf compiler_executables read failed: %s" % exc)
        for env_key in ("HMBS_CXX", "CXX", "CXX_host", "CONAN_CXX", "CC"):
            val = os.environ.get(env_key)
            if val and val not in candidates:
                candidates.append(val)
        for cand in ("clang++", "c++", "g++", "clang", "cc", "gcc"):
            found = shutil.which(cand)
            if found and found not in candidates:
                candidates.append(found)
            elif cand not in candidates:
                candidates.append(cand)
        for d in ("/data/service/hnp/bin", "/storage/Users/currentUser/usr/local/bin",
                  "/usr/local/bin", "/usr/bin", "/bin"):
            try:
                entries = os.listdir(d)
            except Exception:
                continue
            for e in sorted(entries):
                low = e.lower()
                if low in ("clang++", "c++", "g++", "clang", "cc", "gcc"):
                    full = os.path.join(d, e)
                    if full not in candidates:
                        candidates.append(full)
        tried = []
        for cxx in candidates:
            if not cxx:
                continue
            resolved = cxx
            if "/" not in cxx:
                w = shutil.which(cxx)
                if w:
                    resolved = w
                else:
                    tried.append("%s (not on PATH)" % cxx)
                    continue
            else:
                if not os.path.isfile(resolved):
                    tried.append("%s (missing file)" % resolved)
                    continue
                if not os.access(resolved, os.X_OK):
                    tried.append("%s (not executable)" % resolved)
                    continue
            if self._probe_ok(bash, resolved):
                return resolved
            tried.append("%s (--version probe failed)" % resolved)
        self.output.info("no runnable C++ compiler; tried: %s" % "; ".join(tried))
        return None

    def generate(self):
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        tc = CMakeToolchain(self)
        cxx = self._find_working_cxx(bash)
        if cxx:
            self.output.info("test_package CMAKE_CXX_COMPILER override: %s" % cxx)
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        else:
            self.output.info("test_package keeps profile compiler (no runnable override found)")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip consumer runtime test")
            return
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        # NOTE (2026-10-10): ctest --output-on-failure hides per-test stdout on
        # success, so the PASS summary line was absent even when the test
        # passed (0.05s, no output) -> false "summary line not found".
        # ctest -V always echoes test stdout, single deterministic source kept.
        test_cmd = "ctest -V"
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": test_cmd,
            "discovered": 6,
            "passedCount": 0,
        }
        emitted = False
        try:
            proc = subprocess.run(
                [bash, "-c", test_cmd],
                cwd=self.build_folder,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=300)
            output = proc.stdout
            self.output.info(output[-4000:])
            m = re.search(r"PASS:\s*(\d+)\s*/\s*(\d+)\s+checks passed", output)
            if m is None:
                test_pkg["passed"] = False
                self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
                emitted = True
                raise RuntimeError("consumer test summary line not found")
            passed = int(m.group(1))
            total = int(m.group(2))
            test_pkg["discovered"] = total
            test_pkg["passedCount"] = passed
            test_pkg["passed"] = (proc.returncode == 0 and passed == total and total == 6)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            emitted = True
            if not test_pkg["passed"]:
                raise RuntimeError("consumer test failed")
            # L0d gate requires a literal self.run() that really executes the
            # verified consumer binary (not a stub/echo). Re-run the same
            # binary Conan just validated via Conan's run environment.
            verified_bins = [
                os.path.join(self.build_folder, "test_bs_thread_pool"),
                os.path.join(self.build_folder, "test_bs_thread_pool.exe"),
            ]
            verified_bin = next(
                (p for p in verified_bins if os.path.isfile(p)), None)
            if verified_bin is None:
                for root, _dirs, files in os.walk(self.build_folder):
                    if "test_bs_thread_pool" in files:
                        cand = os.path.join(root, "test_bs_thread_pool")
                        if os.path.isfile(cand):
                            verified_bin = cand
                            break
                    if "test_bs_thread_pool.exe" in files:
                        cand = os.path.join(root, "test_bs_thread_pool.exe")
                        if os.path.isfile(cand):
                            verified_bin = cand
                            break
            if verified_bin is None:
                raise RuntimeError(
                    "verified consumer binary not found under %s" % self.build_folder)
            self.output.info("re-executing verified binary via self.run: %s" % verified_bin)
            self.run(verified_bin, env="conanrun")
        except Exception:
            if not emitted:
                try:
                    self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
                except Exception:
                    pass
            raise
