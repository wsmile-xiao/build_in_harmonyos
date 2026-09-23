#!/usr/bin/env python3
"""Conan recipe — libhwy 1.3.0 (Google Highway SIMD, CMake).

Google Highway provides portable SIMD/vector intrinsics. On HarmonyOS
aarch64 the NEON target path is selected automatically. Zero runtime
dependencies. Upstream tests run through Highway's standalone
GTest-compatible runner (HWY_TEST_STANDALONE), so no network download
of googletest is needed.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get


class LibhwyConan(ConanFile):
    name = "libhwy"
    version = "1.3.0"
    description = "Performance-portable SIMD/vector intrinsics library"
    license = "Apache-2.0"
    homepage = "https://github.com/google/highway"
    url = "https://github.com/google/highway"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)
        self.folders.build = "_build"
        self.folders.generators = "_build/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake has no HarmonyOS platform module; select the Linux
            # branch so upstream picks the Linux/NEON code paths.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
            # Skip the link step during compiler detection: some workers
            # lack the libxml2 shared library that lld wants to load.
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        upstream_tests = self.options.with_upstream_tests
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_ENABLE_CONTRIB"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["HWY_ENABLE_INSTALL"] = "ON"
        tc.variables["HWY_ENABLE_TESTS"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_FORCE_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # Highway's native runner keeps CTest discovery without downloading GTest.
        tc.variables["HWY_TEST_STANDALONE"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_WARNINGS_ARE_ERRORS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests and can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream CTest suite and emit the HMBS evidence marker."""
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        def _sh(cmd, timeout):
            return subprocess.run(
                [bash, "-c", cmd], cwd=self.build_folder,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=timeout)

        discovered = 0
        listed = _sh("ctest -N", 300)
        match = re.search(r"Total Tests:\s*(\d+)", listed.stdout)
        if match:
            discovered = int(match.group(1))
        if discovered == 0:
            self.output.error("ctest -N reported no upstream tests:\n" + listed.stdout[-2000:])
            raise RuntimeError("upstream tests produced no executable test cases")

        result = _sh("ctest --output-on-failure", 5400)
        self.output.info("ctest exit=%s tail:\n%s" % (result.returncode, result.stdout[-4000:]))
        passed = 0
        failed = 0
        summary = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", result.stdout)
        if summary:
            failed = int(summary.group(2))
            passed = int(summary.group(3)) - failed
        else:
            passed = len(re.findall(r"Test\s+#\d+:.*\bPassed\b", result.stdout))
            failed = len(re.findall(r"Test\s+#\d+:.*\bFailed\b", result.stdout))
        executed = passed + failed
        if executed == 0 or executed != discovered:
            self.output.error("ctest parsed %d/%d tests, returncode=%s" % (executed, discovered, result.returncode))
            raise RuntimeError("could not verify upstream test execution count")
        status = "passed" if (result.returncode == 0 and failed == 0) else "failed"
        upstream = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        if status != "passed":
            raise RuntimeError("upstream tests failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["hwy"]
        self.cpp_info.set_property("cmake_file_name", "hwy")
        self.cpp_info.set_property("cmake_target_name", "hwy::hwy")
        self.cpp_info.set_property("pkg_config_name", "libhwy")
        if not self.options.shared:
            self.cpp_info.defines.append("HWY_STATIC_DEFINE")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
