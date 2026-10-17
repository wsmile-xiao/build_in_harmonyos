#!/usr/bin/env python3
"""Conan test_package for kanzi-cpp — exercises the real public API.

Builds test_kanzi_roundtrip.cpp (in-memory compress/decompress round-trip
through kanzi/io/CompressedOutputStream + CompressedInputStream) and runs
it plus the packaged kanzi CLI round-trip (cli_test.cmake) under ctest.
Emits the HMBS_TEST_PACKAGE_RESULT marker after the ctest run: 2 ctest
cases, both must pass.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KanzicppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, configured, names):
        if configured and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _usable_compilers(self):
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        cc = self._resolve_compiler(compilers.get("c"), ("clang", "cc"))
        cxx = self._resolve_compiler(compilers.get("cpp"),
                                     ("clang++", "c++"))
        return cc, cxx

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
                          errors="replace") as handle:
                    text = handle.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(text)
        except Exception as exc:
            self.output.warning("HMBS diag toolchain fix failed: %s" % exc)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as exc:
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % exc)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E092: same HarmonyOS platform-module fix as the main recipe;
            # without it test_package configure fails with
            # "System is unknown to cmake" (rtrlib precedent).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
            cc, cxx = self._usable_compilers()
            if cc:
                tc.cache_variables["CMAKE_C_COMPILER"] = cc
            if cxx:
                tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        kanzi_pkg = self.dependencies["kanzi-cpp"].package_folder
        tc.variables["KANZI_BIN"] = os.path.join(
            kanzi_pkg, "bin", "kanzi").replace("\\", "/")
        tc.generate()
        if self.settings.os == "OHOS":
            try:
                _conf = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
            except Exception:
                _conf = {}
            try:
                _cc = tc.cache_variables.get("CMAKE_C_COMPILER")
            except Exception:
                _cc = None
            try:
                _cxx = tc.cache_variables.get("CMAKE_CXX_COMPILER")
            except Exception:
                _cxx = None
            self._fix_generated_toolchain_compiler(_conf, _cc, _cxx)

    def build(self):
        variables = {}
        if self.settings.os == "OHOS":
            cc, cxx = self._usable_compilers()
            if cc:
                variables["CMAKE_C_COMPILER"] = cc
            if cxx:
                variables["CMAKE_CXX_COMPILER"] = cxx
        cmake = CMake(self)
        cmake.configure(variables=variables)
        cmake.build()

    def _find_last_test_log(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "LastTest.log" in files and root.endswith(
                    os.path.join("Testing", "Temporary")):
                return os.path.join(root, "LastTest.log")
        return None

    def _parse_last_test_log(self, path):
        """Parse LastTest.log. Single source: Testing:/verdict lines."""
        discovered = 0
        verdicts = {}
        current = None
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                head = re.match(r"^\s*\d+/\d+\s+Testing:\s+(\S+)", line)
                if head is not None:
                    current = head.group(1)
                    if current not in verdicts:
                        verdicts[current] = None
                        discovered += 1
                    continue
                if current is None:
                    continue
                if re.match(r"^Test Passed\.", line):
                    verdicts[current] = "passed"
                elif re.match(r"^Test (Failed|Timeout)\.", line):
                    verdicts[current] = "failed"
        passed = sum(1 for v in verdicts.values() if v == "passed")
        return discovered, passed

    def _emit_test_package_result(self, passed, command, discovered,
                                  passed_count):
        marker = {
            "executed": True,
            "passed": passed,
            "command": command,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))

    def test(self):
        # 2 ctest cases: roundtrip (C++ stream API) + cli_roundtrip (CLI).
        # Counts come from Testing/Temporary/LastTest.log (single source),
        # not from hardcoded constants.
        command = "ctest --output-on-failure"
        # OHOS: /system/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test command with the bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f'{bash} -c "ctest --output-on-failure"',
                     cwd=self.build_folder, env="conanrun")
            ctest_ok = True
        except Exception:
            ctest_ok = False
        log_path = self._find_last_test_log()
        if log_path is not None:
            discovered, passed_count = self._parse_last_test_log(log_path)
            passed = ctest_ok and discovered == 2 and passed_count == 2
            self._emit_test_package_result(passed, command,
                                           discovered, passed_count)
            if not passed:
                raise RuntimeError(
                    f"test_package ctest failed: {passed_count}/"
                    f"{discovered} passed (see {log_path})")
        else:
            # No deterministic log source: report honestly, never fabricate.
            self._emit_test_package_result(False, command, 0, 0)
            raise RuntimeError(
                "test_package produced no LastTest.log under %s"
                % self.build_folder)
