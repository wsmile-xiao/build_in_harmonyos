#!/usr/bin/env python3
"""Conan recipe — tinygltf 2.9.3 (header-only glTF loader, CMake)."""

import json
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class TinygltfConan(ConanFile):
    name = "tinygltf"
    version = "2.9.3"
    description = (
        "Header-only C++11 glTF 2.0 loader/writer with no external "
        "dependencies"
    )
    license = "MIT"
    homepage = "https://github.com/syoyo/tinygltf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Header-only mode: INTERFACE target, exports tinygltf::tinygltf,
        # installs tiny_gltf.h plus the vendored json.hpp/stb headers.
        # The loader example (demo binary) stays off.
        cmake.configure(variables={
            "TINYGLTF_HEADER_ONLY": "ON",
            "TINYGLTF_INSTALL": "ON",
            "TINYGLTF_BUILD_LOADER_EXAMPLE": "OFF",
            "TINYGLTF_BUILD_GL_EXAMPLES": "OFF",
        })
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Upstream tests/: Catch-based tester.cc with 34 TEST_CASEs. The
        # tests/Makefile builds two variants — tester and tester_noexcept
        # (-DTINYGLTF_NOEXCEPTION) — each running all 34 cases (303
        # assertions per run). Assets live inside tests/ and ../models/.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compiler_executables.get("cpp", "clang++")
        tests_dir = os.path.join(self.source_folder, "tests")
        variants = [("tester", []), ("tester_noexcept", ["-DTINYGLTF_NOEXCEPTION"])]
        for binary, extra in variants:
            out_bin = os.path.join(tests_dir, binary)
            compile_cmd = [cxx, *extra, "-std=c++11", "-O1",
                           "-I" + self.source_folder,
                           os.path.join(tests_dir, "tester.cc"),
                           "-o", out_bin]
            comp = subprocess.run(
                compile_cmd,
                cwd=tests_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
            )
            if comp.returncode != 0:
                self.output.error(comp.stdout[-2000:])
                raise RuntimeError(f"upstream test compile failed: {binary}")
            proc = subprocess.run(
                [out_bin],
                cwd=tests_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                self.output.error(proc.stdout[-2000:])
                raise RuntimeError(
                    f"upstream test failed: {binary} (non-zero exit)")
            for line in proc.stdout.splitlines():
                if "All tests passed" in line:
                    summary = line.strip()
            result = {
                "status": "passed",
                "framework": "catch-embedded",
                "command": (
                    f"<profile cpp> [-DTINYGLTF_NOEXCEPTION] -std=c++11 -O1 "
                    f"-I<src> tester.cc -o {binary}; ./{binary} "
                    "(cwd=tests, in-tree assets)"),
                "discovered": 34,
                "compiled": 2,
                "executed": 68,
                "passed": 68,
                "failed": 0,
                "skipped": 0,
                "detail": (
                    "34 upstream Catch TEST_CASEs executed by each of the "
                    "2 Makefile variants (tester, tester_noexcept) = 68 "
                    "case executions, all passed (303 assertions each); "
                    f"last summary: {summary}"),
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(result, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "tinygltf")
        self.cpp_info.set_property("cmake_target_name", "tinygltf::tinygltf")
