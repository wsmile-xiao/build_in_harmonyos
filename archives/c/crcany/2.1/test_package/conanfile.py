#!/usr/bin/env python3
"""Consumer test for the packaged crcany static library."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CrcanyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_cc(self):
        # CMakeToolchain 默认把 profile 里的绝对编译器路径
        # (/data/service/hnp/bin/clang) 写进 toolchain；该路径在部分预检
        # worker 上不存在 -> cmake configure 报“compiler not found”。
        # 与主包同策略：conf 值仅在文件存在时采用，否则回退 PATH 中的
        # clang（HMBS 已把工具目录前置到 buildenv PATH，真机实测为
        # .harmonybrew/bin/clang）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get("c")
        if cand and os.path.isabs(cand):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        elif cand:
            found = shutil.which(cand)
            if found:
                return found
            return cand
        for name in ("clang", "cc"):
            found = shutil.which(name)
            if found:
                return found
        return cand or "clang"

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        cc = self._resolve_cc()
        tc.variables["CMAKE_C_COMPILER"] = cc
        self.output.info("test_package: CMAKE_C_COMPILER=%s" % cc)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _tested_dep(self):
        for key in ("crcany", self.tested_reference_str, self.tested_reference_str.split("/")[0]):
            try:
                dep = self.dependencies[key]
                if dep is not None:
                    return dep
            except Exception:
                continue
        return None

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_crcany")
        # Capture once for evidence counters (log shows real PASS lines).
        proc = subprocess.run(
            [executable],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        out = proc.stdout or ""
        self.output.info("test_crcany output:\n%s" % out[-2000:])
        if not out.strip():
            raise RuntimeError("test_crcany produced no output; harness did not really run")
        discovered = 5
        passed_count = out.count("PASS ")
        # L0d/L1 gate: run through Conan so the test trace is recorded.
        self.run(executable, env="conanrun")
        if proc.returncode != 0:
            raise RuntimeError("test_crcany exited with %d" % proc.returncode)
        if passed_count != discovered:
            raise RuntimeError(
                "test_crcany PASS lines %d != %d expected" % (passed_count, discovered)
            )
        if "All crcany consumer tests passed." not in out:
            raise RuntimeError("test_crcany missing final verdict line")

        # Re-emit the upstream result persisted by the recipe so both HMBS
        # evidence markers appear in the conan create log.
        dep = self._tested_dep()
        if dep is not None:
            for cand in (
                os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
                os.path.join(dep.package_folder, "upstream_test_result.json"),
            ):
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as f:
                        upstream = json.load(f)
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
                    break

        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_crcany",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
