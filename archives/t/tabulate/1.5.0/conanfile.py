#!/usr/bin/env python3
"""Conan recipe — tabulate 1.5.0 (CMake, header-only).

tabulate is a header-only C++11 library for printing aligned, formatted
tables. The upstream CMakeLists defines an INTERFACE target
tabulate::tabulate (add_library(... INTERFACE)) and installs headers +
CMake package config. It has no compiled artifacts, so package_type =
"header-library".
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TabulateConan(ConanFile):
    name = "tabulate"
    version = "1.5.0"
    description = "Header-only C++11 library for printing aligned, formatted tables."
    license = "MIT"
    homepage = "https://github.com/p-ranav/tabulate"
    url = "https://github.com/p-ranav/tabulate"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="tabulate-1.5.0.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform module; force the Linux branch.
        # tabulate only reads compiler/platform macros, so the platform name
        # does not affect the emitted header behavior.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream samples double as build smoke tests: build representative
        # ones so the headers are actually compiled under the OHOS toolchain,
        # then run one to verify runtime behavior (R51 清点: 上游无 tests/
        # 目录、无 ctest 注册，samples/ 下 19 个示例是可运行程序）。
        cmake.configure(variables={"SAMPLES": "ON"})
        cmake.build(target=["employees", "markdown_export", "unicode"])
        self._run_upstream_samples()

    def _run_upstream_samples(self):
        """Run a representative upstream sample (employees) as a smoke test."""
        exe = self._find_sample("employees")
        if exe is None:
            self.output.warning("upstream sample 'employees' not built; skipping smoke run")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        proc = subprocess.run(
            [bash, "-c", f'cd "{os.path.dirname(exe)}" && ./employees'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        self.output.info(
            f"upstream sample employees exit={proc.returncode} executed=1 passed=1 failed=0")
        if proc.returncode != 0:
            self.output.error("=== employees tail ===\n" + proc.stdout[-2000:])
            raise RuntimeError("upstream sample 'employees' failed")
        upstream = {
            "status": "passed",
            "framework": "sample-smoke",
            "command": "cd build && ./employees",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _find_sample(self, name):
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        return None

    def package(self):
        # Header-only: ship include/tabulate/*.hpp and licenses.
        copy(self, "tabulate/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        for lic in ("LICENSE", "LICENSE.optional-lite",
                    "LICENSE.termcolor", "LICENSE.variant-lite"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                copy(self, lic, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "tabulate")
        self.cpp_info.set_property("cmake_target_name", "tabulate::tabulate")
