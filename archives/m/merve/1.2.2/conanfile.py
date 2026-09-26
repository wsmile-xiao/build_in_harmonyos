#!/usr/bin/env python3
"""Conan recipe for merve 1.2.2 on HarmonyOS PC."""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MerveConan(ConanFile):
    name = "merve"
    version = "1.2.2"
    description = ("Fast C++ lexer that statically extracts named exports and "
                   "re-export specifiers from CommonJS modules")
    license = ("MIT", "Apache-2.0")
    homepage = "https://github.com/nodejs/merve"
    url = "https://github.com/nodejs/merve"
    topics = ("commonjs", "lexer", "exports", "javascript", "static-analysis")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, filename="merve-1.2.2.tar.gz", **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        if self.settings.os == "OHOS":
            # OHOS ships pthread symbols in libc; CMake's cross probe would otherwise
            # pick the non-existent -lpthreads compatibility name.
            tc.cache_variables["CMAKE_HAVE_LIBC_PTHREAD"] = True
        tc.cache_variables["MERVE_TESTING"] = True
        tc.cache_variables["MERVE_BENCHMARKS"] = False
        tc.cache_variables["MERVE_USE_SIMDUTF"] = False
        tc.cache_variables["MERVE_SANITIZE"] = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        gtest = self.dependencies["gtest"]
        tc.cache_variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not can_run(self):
            self.output.info("HMOS_UPSTREAM_TEST_RESULT=cross-building, execution on device only")
            return

        listing = os.path.join(self.build_folder, "hmos_ctest_list.txt")
        self.run(f'ctest --test-dir "{self.build_folder}" -N > "{listing}" 2>&1', env="conanbuild")
        # ctest -N 每行形如 `  Test #1: real_world_tests.esbuild_hint_style`（行首有缩进）。
        entry = re.compile(r"\s*Test\s+#\d+:")
        configured = 0
        with open(listing, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if entry.match(line):
                    configured += 1
        if configured < 100:
            raise ConanException(
                "upstream GoogleTest suite was not configured (ctest lists "
                f"{configured} of >=100 expected tests); see {listing}"
            )

        log = os.path.join(self.build_folder, "hmos_ctest.log")
        self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure '
                f'> "{log}" 2>&1', env="conanbuild")
        # 逐项结果行形如 `  1/101 Test   #1: real_world_tests.esbuild_hint_style ... Passed 0.04 sec`；
        # 零失败时 ctest 汇总行是 `100% tests passed out of 101`（不含 "tests failed"），
        # 因此按逐项行计数，不解析汇总句。
        result_line = re.compile(r"^\s*\d+/\d+\s+Test\s+#\d+:")
        total = passed = 0
        with open(log, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if result_line.match(line):
                    total += 1
                    if " Passed" in line:
                        passed += 1
        if total == 0:
            raise ConanException("ctest reported no test results; see " + log)
        failed = total - passed
        self.output.info("HMOS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed",
            "framework": "gtest+ctest",
            "source_declared_total": 100,
            "configured": configured,
            "passed": passed,
            "total": total,
            "failed": total - passed,
            "note": ("100 GoogleTest TEST declarations in tests/real_world_tests.cpp (65) "
                     "and tests/c_api_tests.cpp (35), enumerated by gtest_discover_tests, "
                     "plus the upstream compile-only c_api_compile_test"),
        }, ensure_ascii=False))

    def package(self):
        CMake(self).install()
        for lic in ("LICENSE-MIT", "LICENSE-APACHE"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "merve")
        self.cpp_info.set_property("cmake_target_name", "merve::merve")
        self.cpp_info.set_property("pkg_config_name", "merve")
        self.cpp_info.libs = ["merve"]
