#!/usr/bin/env python3
"""Conan recipe for libcanard 3.3.0 (Cyphal/CAN transport in C).

Upstream OpenCyphal/libcanard ships no install target: the documented
integration is copying libcanard/canard.c and libcanard/canard.h into the
consuming project. This recipe follows the linenoise pattern and generates
a small CMakeLists.txt in build() to compile canard.c into a static/shared
library and install the public headers.

Upstream tests: tests/ holds a Catch2 suite (33 TEST_CASE) driven by ctest
(3 matrices x 4 arch/std variants = 12 ctest tests). The suite is configured
in build() with static analysis and sanitizers disabled (clang-tidy and
sanitizer runtimes are not available on the OHOS device) and executed via
ctest; the result is emitted as HMBS_UPSTREAM_TEST_RESULT and persisted to
res/upstream_test_result.json so test_package can re-emit it on cache hits.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class LibcanardConan(ConanFile):
    name = "libcanard"
    version = "3.3.0"
    description = "Compact implementation of the Cyphal/CAN protocol in C for high-integrity real-time embedded systems"
    license = "MIT"
    homepage = "https://github.com/OpenCyphal/libcanard"
    topics = ("cyphal", "can", "uavcan", "embedded")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcanard is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def _ensure_writable_tmp(self):
        # True-machine /tmp may be read-only (HMBS readonly_tmp). Prefer the
        # injected TMPDIR/TMP/TEMP; fall back to a writable dir under the
        # build folder so cmake/ctest/python-tempfile never touch /tmp.
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if val and os.path.isdir(val) and os.access(val, os.W_OK):
                return val
        fallback = os.path.join(self.build_folder, ".hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = fallback
        return fallback

    def _ctest(self):
        # Prefer the hmbs-probed absolute tool path; fall back to PATH lookup.
        try:
            cmake_path = self.conf.get("user.hmbs:cmake_path", default=None, check_type=str)
        except Exception:
            cmake_path = None
        cmake_path = cmake_path or os.environ.get("HMBS_CMAKE")
        if cmake_path:
            sibling = os.path.join(os.path.dirname(cmake_path), "ctest")
            if os.path.isfile(sibling):
                return sibling
        return "ctest"

    def _reset_cmake_cache(self):
        # build() configures two different source dirs (tests/ for the
        # upstream ctest suite, then the generated top-level CMakeLists for
        # the library) into the same Conan binary dir. CMake refuses to
        # switch source dirs on top of an existing cache ("does not match
        # the source ... used to generate cache"), so drop the cache between
        # configures. Only CMake-generated state is removed; the persisted
        # upstream_test_result.json lives directly under build_folder and is
        # left untouched.
        for root, dirs, files in os.walk(self.build_folder):
            if "CMakeCache.txt" in files:
                try:
                    os.remove(os.path.join(root, "CMakeCache.txt"))
                except OSError:
                    pass
                for stale in ("CMakeFiles", "_CMakeFiles"):
                    stale_dir = os.path.join(root, stale)
                    if os.path.isdir(stale_dir):
                        shutil.rmtree(stale_dir, ignore_errors=True)
                for stale_file in ("cmake_install.cmake", "CTestTestfile.cmake",
                                   "Makefile", "build.ninja"):
                    stale_path = os.path.join(root, stale_file)
                    try:
                        if os.path.isfile(stale_path):
                            os.remove(stale_path)
                    except OSError:
                        pass

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        cmake_content = """cmake_minimum_required(VERSION 3.15)
project(canard C)

add_library(canard libcanard/canard.c)
target_include_directories(canard PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/libcanard>
    $<INSTALL_INTERFACE:include/canard>)

install(TARGETS canard
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib)
install(FILES libcanard/canard.h libcanard/_canard_cavl.h DESTINATION include/canard)
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)

        tests_src = os.path.join(self.source_folder, "tests")
        cmake = CMake(self)
        self._reset_cmake_cache()
        cmake.configure(build_script_folder=tests_src, cli_args=[
            "-DNO_STATIC_ANALYSIS=ON",
            "-DNO_CANARD_SANITIZER=ON",
        ])
        cmake.build()
        result = self._run_upstream_tests()
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8", newline="\n") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            raise ConanException("libcanard upstream tests failed")

        self._reset_cmake_cache()
        cmake.configure()
        cmake.build()

    def _run_upstream_tests(self):
        ctest = self._ctest()
        command = f"{ctest} --output-on-failure"
        try:
            proc = subprocess.run(
                [ctest, "--output-on-failure"],
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
            output = proc.stdout or ""
        except Exception as exc:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 12,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": f"ctest harness could not run: {exc!r}",
            }
        self.output.info(output[-6000:])
        if "No tests were found" in output:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "ctest found no tests (silent-skip trap)",
            }
        match = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", output)
        if not match:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "could not parse ctest summary line",
            }
        percent, failed, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
        passed = total - failed
        status = "passed" if (percent == 100 and failed == 0 and total > 0) else "failed"
        return {
            "status": status,
            "framework": "ctest",
            "command": command,
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["canard"]
        self.cpp_info.set_property("cmake_file_name", "canard")
        self.cpp_info.set_property("cmake_target_name", "canard::canard")
