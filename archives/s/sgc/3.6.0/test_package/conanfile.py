#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test package for sgc 3.6.0.

Conan L1 official test. Builds a small C++ consumer that exercises the core
sgc (libsigc++) API (signal/slot/connection/emit), then runs it to validate
that the packaged library is functional on HarmonyOS PC.
"""

import json
import os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class SgcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Writable tmp for compiler temp files (device /tmp is read-only).
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("sgc_test_tmpdir")
        super().generate() if hasattr(super(), "generate") else None

    def _resolve_compiler(self, kind):
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        key = "c" if kind == "c" else "cpp"
        val = exes.get(key) or ""
        first = val.split()[0] if val else ""
        if first and os.path.isabs(first) and os.path.isfile(first):
            return first
        if first and not os.path.isabs(first):
            return first
        if first and os.path.isabs(first) and not os.path.isfile(first):
            self.output.warning(
                "conf compiler '%s' unusable; falling back to PATH" % val
            )
        names = ("clang", "cc") if kind == "c" else ("clang++", "c++")
        for name in names:
            found = _shutil.which(name)
            if found:
                return found
        return ""

    def build(self):
        # If the profile compiler is stale, force CMake onto the resolved one.
        # CMakeToolchain already ran in generate(); patch its toolchain file.
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        if cc or cxx:
            tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(tc_file):
                try:
                    with open(tc_file, encoding="utf-8") as handle:
                        content = handle.read()
                    orig = content
                    for var, path in (
                        ("CMAKE_C_COMPILER", cc),
                        ("CMAKE_CXX_COMPILER", cxx),
                    ):
                        if not path:
                            continue
                        cur = ""
                        for line in content.splitlines():
                            if line.strip().startswith("set(%s " % var):
                                # set(CMAKE_C_COMPILER "/stale/path" ...)
                                parts = line.split('"')
                                if len(parts) >= 2:
                                    cur = parts[1]
                                break
                        if cur and os.path.isabs(cur) and os.path.isfile(cur):
                            continue
                        if cur and (not os.path.isabs(cur)):
                            continue
                        if cur and os.path.isabs(cur) and not os.path.isfile(cur):
                            content = content.replace(cur, path)
                            self.output.info(
                                "test_package: %s stale '%s' -> '%s'"
                                % (var, cur, path)
                            )
                    if content != orig:
                        with open(tc_file, "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(content)
                except OSError as exc:
                    self.output.warning("patch conan_toolchain failed: %s" % exc)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_package")
        log_path = os.path.join(self.build_folder, "test_package.log")
        try:
            self.run('"%s" > "%s" 2>&1' % (binary, log_path), env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        # test_package.cc prints [1]..[5] plus final OK; count real checkpoints.
        discovered = 5
        passed_count = sum(1 for i in ("[1]", "[2]", "[3]", "[4]", "[5]") if i in out)
        ok_tail = "test sgc 3.6.0: OK" in out
        passed = passed_count == discovered and ok_tail
        marker = {
            "executed": True,
            "passed": passed,
            "command": "./test_package",
            "discovered": discovered,
            "passedCount": passed_count if not passed else discovered,
        }
        # If binary failed but markers partial, passedCount reflects reality.
        if not passed:
            marker["passedCount"] = passed_count
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        self._emit_upstream_result()
        if not passed:
            raise ConanException(
                "test_package failed: %d/%d checkpoints passed" % (passed_count, discovered)
            )

    def _emit_upstream_result(self):
        try:
            dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        except Exception:
            dep = None
            for _name, d in self.dependencies.items():
                dep = d
                break
        if dep is None:
            raise ConanException("tested dependency not found for upstream re-emit")
        path = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
        if not os.path.isfile(path):
            raise ConanException("hmbs_upstream.json not found in package")
        with open(path, "r", encoding="utf-8") as handle:
            result = json.load(handle)
        ok_shape = (
            isinstance(result, dict)
            and result.get("status") == "passed"
            and int(result.get("discovered", 0)) > 0
            and int(result.get("executed", 0)) == int(result.get("discovered", 0))
            and int(result.get("passed", 0)) == int(result.get("discovered", 0))
            and int(result.get("failed", 0)) == 0
            and int(result.get("skipped", 0)) == 0
        )
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        if not ok_shape:
            raise ConanException("upstream test evidence invalid: %s" % (result,))
