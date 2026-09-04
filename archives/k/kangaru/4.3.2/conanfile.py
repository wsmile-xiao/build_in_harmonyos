#!/usr/bin/env python3
"""Conan recipe — kangaru 4.3.2 (CMake, header-only dependency injection library).

kangaru is a header-only C++11 library: `add_library(kangaru INTERFACE)` +
`install(DIRECTORY include/kangaru ...)`. No compiled objects are produced,
so this recipe packages the public headers and the CMake package config.

Platform notes:
  - The upstream test suite (21 ctest targets / 109 TEST_CASE across
    test/src/*.cpp) requires Catch2, which upstream vendors as a git submodule
    under test/third_party/Catch2. The official tarball does NOT contain the
    submodule payload (empty directory), so the recipe depends on the
    conan-provided catch2 for tests. Tests are gated behind KANGARU_TEST and
    exercised in build() when self.tested (conan create).
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KangaruConan(ConanFile):
    name = "kangaru"
    version = "4.3.2"
    description = "A dependency injection library for C++11, designed with a focus on compile time and runtime performances"
    license = "MIT"
    homepage = "https://github.com/gracicot/kangaru"
    url = "https://github.com/gracicot/kangaru"
    topics = ("dependency-injection", "di", "c++11", "header-only")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Catch2 is only needed to build the upstream test suite; it is not a
        # runtime/consumer dependency of the header-only library itself.
        self.test_requires("catch2/2.13.10-r0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate Catch2Config.cmake so upstream test/CMakeLists.txt's
        # find_package(Catch2) succeeds; otherwise it falls back to the empty
        # third_party/Catch2 submodule directory (not shipped in the tarball).
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # kangu is a pure header-only library; keep the upstream defaults for
        # install/export and never build examples/benchmarks in the package.
        tc.variables["KANGARU_INSTALL"] = "ON"
        tc.variables["KANGARU_BUILD_EXAMPLES"] = "OFF"
        tc.variables["KANGARU_BENCHMARK"] = "OFF"
        tc.variables["KANGARU_EXPORT"] = "ON"
        # Exercise the full upstream test suite during conan create (package
        # build). kangaru is header-only and the suite runs in seconds, so the
        # tests are always built and run for every package revision.
        tc.variables["KANGARU_TEST"] = "ON"
        tc.variables["KANGARU_TEST_CXX14"] = "ON"
        tc.variables["KANGARU_TEST_CXX17"] = "ON"
        tc.variables["KANGARU_REVERSE_DESTRUCTION"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests(cmake)

    def _run_upstream_tests(self, cmake):
        """Run the upstream Catch2 test suite via ctest and emit a machine-readable marker.

        Source audit: test/src/*.cpp contains 109 TEST_CASE in 19 files,
        registered as 21 ctest targets in test/CMakeLists.txt (17 regular +
        2 compile-time error targets + generic_lambdas(C++14) + noexcept_invoke(C++17)).
        Certain targets are EXCLUDE_FROM_ALL build-time checks, so only the
        ctest-registered runnable tests are executed here.
        """
        bin_dir = os.path.join(self.build_folder, "bin")
        out = ""
        try:
            result = subprocess.run(
                ["ctest", "--output-on-failure"],
                cwd=self.build_folder, capture_output=True, text=True, timeout=1800)
            out = (result.stdout or "") + (result.stderr or "")
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            self.output.error("upstream ctest timed out")
            out = "TIMEOUT"
            returncode = 124
        self.output.info("\n".join(out.splitlines()[-15:]))

        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", out)
        if m:
            pct, failed, total = int(m.group(1)), int(m.group(2)), int(m.group(3))
            status = "passed" if failed == 0 else "failed"
        elif returncode == 0:
            pct, failed, total, status = 100, 0, 0, "passed"
        else:
            pct, failed, total, status = 0, 1, 0, "failed"

        marker = {
            "status": status,
            "framework": "ctest/catch2",
            "command": "ctest --output-on-failure",
            "discovered": total,
            "executed": total,
            "passed": total - failed,
            "failed": failed,
            "pct": pct,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []  # header-only library: no compiled artifacts
        self.cpp_info.set_property("cmake_file_name", "kangaru")
        self.cpp_info.set_property("cmake_target_name", "kangaru::kangaru")