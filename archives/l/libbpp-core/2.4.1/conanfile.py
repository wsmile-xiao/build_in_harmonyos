#!/usr/bin/env python3
"""Conan recipe for libbpp-core 2.4.1 (Bio++ Core Library, CMake).

Upstream builds both static and shared bpp-core libraries and registers
19 ctest cases (one per test/test_*.cpp). No external Conan dependencies.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibbppCoreConan(ConanFile):
    name = "libbpp-core"
    version = "2.4.1"
    description = "Bio++ Core Library: C++ classes for bioinformatics and numerical calculus"
    license = "CECILL-2.1"
    homepage = "https://github.com/BioPP/bpp-core"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream cmake_minimum_required(2.8.11); modern CMake needs a policy floor.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Build the upstream test suite (test/ registers one ctest per test_*.cpp).
        tc.cache_variables["BUILD_TESTING"] = True
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run ctest and emit HMBS_UPSTREAM_TEST_RESULT with real counts."""
        discovered = 19  # audited: 19 test/test_*.cpp files in v2.4.1
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        # Ensure freshly built shared libs resolve for the test binaries.
        lib_dirs = set()
        for root, _dirs, files in os.walk(self.build_folder):
            if any(n.endswith(".so") or n.endswith(".so.4") for n in files):
                lib_dirs.add(root)
        env = dict(os.environ)
        if lib_dirs:
            extra = os.pathsep.join(sorted(lib_dirs))
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = extra + (os.pathsep + prev if prev else "")
        cmd = 'ctest --output-on-failure'
        proc = subprocess.run(
            [bash, "-c", cmd],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
            env=env,
        )
        output = proc.stdout or ""
        self.output.info(output[-4000:])
        executed, passed, failed = self._parse_ctest(output, discovered)
        status = "passed" if (proc.returncode == 0 and failed == 0 and executed == discovered and passed == executed) else "failed"
        # Fail closed: exit 0 with no real tests is not a pass.
        if executed == 0:
            status = "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            raise RuntimeError("upstream ctest failed: executed=%d passed=%d failed=%d" % (executed, passed, failed))

    @staticmethod
    def _parse_ctest(output, discovered):
        executed = 0
        passed = 0
        failed = 0
        # Typical: "100% tests passed, 0 tests failed out of 19"
        m = re.search(r"(\d+)\s+tests passed.*?(\d+)\s+tests failed\s+out of\s+(\d+)", output)
        if m:
            passed = int(m.group(1))
            failed = int(m.group(2))
            total = int(m.group(3))
            executed = passed + failed
            if total != discovered:
                executed = total - 0
                # keep audited discovered; executed is what ran
                executed = passed + failed
            return executed, passed, failed
        m2 = re.search(r"tests passed,\s*(\d+)\s*tests failed\s*out of\s*(\d+)", output)
        if m2:
            failed = int(m2.group(1))
            total = int(m2.group(2))
            passed = total - failed
            executed = total
            return executed, passed, failed
        # Fallback: count "Passed" lines from ctest verbose list.
        passed_lines = len(re.findall(r"Passed\s+.*#\s*\d+", output))
        failed_lines = len(re.findall(r"Failed\s+.*#\s*\d+", output))
        if passed_lines or failed_lines:
            return passed_lines + failed_lines, passed_lines, failed_lines
        return 0, 0, 0

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["bpp-core"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "bpp-core")
        self.cpp_info.set_property("cmake_target_name", "bpp-core-shared")
        self.cpp_info.set_property("pkg_config_name", "bpp-core")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
