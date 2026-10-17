#!/usr/bin/env python3
"""Conan test_package for rtosc 0.3.1 — consumer verification.

Builds test_rtosc.cpp against the packaged rtosc::rtosc target and runs
11 real assertions (C message/bundle/version/match + C++ Ports dispatch).
Parses the CHECK-OK lines from the captured log for the
HMBS_TEST_PACKAGE_RESULT marker, then re-emits the upstream evidence
persisted by the recipe build (no hardcoded copies of those numbers).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


# Audited from test_rtosc.cpp: 11 check() invocations, each emitting exactly
# one CHECK-OK line on success (CHECK-FAIL + non-zero exit otherwise).
TEST_PACKAGE_TOTAL = 11


class RtoscTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, configured, names):
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag compiler env failed: %s" % e)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"), ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_rtosc")
        log_path = os.path.join(self.build_folder, "test_rtosc.log")
        try:
            self.run('"%s" > "%s" 2>&1' % (binary, log_path), env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        if not out.strip():
            raise ConanException("test_package log empty; refusing to claim a pass")
        passed_count = sum(
            1 for line in out.splitlines() if line.startswith("CHECK-OK:")
        )
        fail_lines = sum(
            1 for line in out.splitlines() if line.startswith("CHECK-FAIL:")
        )
        discovered = TEST_PACKAGE_TOTAL
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered and fail_lines == 0,
            "command": "./test_rtosc (C message/bundle/version/match + C++ Ports dispatch)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        try:
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
        except Exception:
            pass
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                "test_package failed: %d/%d checks passed (%d failures)" % (
                    passed_count, discovered, fail_lines))

    def _emit_upstream_result(self):
        dep = self.dependencies["rtosc"]
        path = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
        if not os.path.isfile(path):
            raise ConanException("hmbs_upstream.json not found in package")
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        ok_shape = (
            isinstance(result, dict)
            and result.get("status") == "passed"
            and result.get("framework") == "ctest"
            and int(result.get("discovered", 0)) == 28
            and int(result.get("executed", 0)) == 28
            and int(result.get("passed", 0)) == 28
            and int(result.get("failed", 0)) == 0
            and int(result.get("skipped", 0)) == 0
        )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        try:
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result), flush=True)
        except Exception:
            pass
        if not ok_shape:
            raise ConanException("upstream test evidence invalid: %s" % (result,))
