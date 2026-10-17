#!/usr/bin/env python3
"""Conan recipe — lwrb 3.3.0 (CMake, pure C ring buffer library).

lwrb is a lightweight, general-purpose ring buffer manager for embedded
systems. Upstream is CMake-based and produces two targets when the root
CMakeLists is configured top-level: a dev-only demo executable and the
`lwrb` core library (plus a dev-only `lwrb_ex` extended library guarded by
LWRB_DEV whose functions are NOT declared in the public header).

The GitHub source archive ships EMPTY submodules (third_party/Unity and
third_party/sanitizers-cmake). The upstream test project (lwrb/test) builds
Unity-based unit tests (test.c = 5 cases, test_ex.c = 10 cases guarded by
TEST), so this recipe restores Unity 2.7.0 and sanitizers-cmake from their
official releases and wires test_ex.c into the test project via a minimal
patch (0002), then builds and runs both suites inside `conan create`.

On OHOS the root CMakeLists is configured with LWRB_BUILD_DEV=OFF (patch
0001): only the `lwrb` target is built, the dev executable and its PUBLIC
WIN32/_DEBUG/CONSOLE/LWRB_DEV definitions are skipped, and install rules
cover the core library + the single public header lwrb/lwrb.h.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LwrbConan(ConanFile):
    name = "lwrb"
    version = "3.3.0"
    description = "Lightweight general purpose ring buffer with optimizations for embedded systems"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwrb"
    url = "https://github.com/MaJerle/lwrb"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub archives omit submodule content; the upstream test project
        # requires third_party/Unity and third_party/sanitizers-cmake.
        get(self, **self.conan_data["unity"],
            destination="third_party/Unity", strip_root=True)
        get(self, **self.conan_data["sanitizers_cmake"],
            destination="third_party/sanitizers-cmake", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: keep BUILD_SHARED_LIBS in sync with the shared option
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Skip the dev-only demo executable branch (patch 0001)
        tc.variables["LWRB_BUILD_DEV"] = "OFF"
        # CMake has no registered Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG is empty and SOVERSION alone
        # produces no DT_SONAME (L5a gate). Provide the linker flag explicitly.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Configure+build+run the upstream Unity test project (lwrb/test).

        The test project is an independent CMake project (project
        lwrb-testing) with its own CMakeLists; it uses the same OHOS
        toolchain as the library. Patch 0002 wires test_ex.c (10 Unity
        cases) into it as lwrb_test_ex alongside the original lwrb_test
        (5 Unity cases) so the full upstream suite is instantiated.
        """
        test_src = os.path.join(self.source_folder, "lwrb", "test")
        test_build = os.path.join(self.build_folder, "upstream-test")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        cmake_bin = shutil.which("cmake")
        if cmake_bin is None:
            raise RuntimeError("cmake not found in PATH")

        def run(cmd, cwd=None):
            proc = subprocess.run(cmd, env=os.environ.copy(), cwd=cwd,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True)
            return proc

        cfg = run([cmake_bin, "-S", test_src, "-B", test_build,
                   f"-DCMAKE_TOOLCHAIN_FILE={toolchain}"])
        if cfg.returncode != 0:
            self.output.error("upstream test configure failed:\n" + cfg.stdout[-2000:])
            raise RuntimeError("upstream test configure failed")
        bld = run([cmake_bin, "--build", test_build, "-j", "2"])
        if bld.returncode != 0:
            self.output.error("upstream test build failed:\n" + bld.stdout[-2000:])
            raise RuntimeError("upstream test build failed")

        results = []
        for exe, declared in (("lwrb_test", 5), ("lwrb_test_ex", 10)):
            exe_path = os.path.join(test_build, exe)
            if not os.path.isfile(exe_path):
                self.output.error(f"upstream test executable missing: {exe_path}")
                raise RuntimeError(f"upstream test executable missing: {exe}")
            proc = run([exe_path], cwd=test_build)
            out = proc.stdout
            # Unity prints one "PASS"/"FAIL" line per executed test
            passed = len(re.findall(r":PASS\b", out))
            failed = len(re.findall(r":FAIL\b", out))
            summary = re.search(r"(OK|FAILED) \((\d+) tests?\)", out)
            reported = int(summary.group(2)) if summary else passed + failed
            ok = proc.returncode == 0 and failed == 0 and reported == declared
            results.append({"exe": exe, "declared": declared, "executed": reported,
                            "passed": passed, "failed": failed,
                            "exit": proc.returncode, "ok": ok,
                            "tail": out[-600:]})
            self.output.info(f"{exe}: declared={declared} executed={reported} "
                             f"passed={passed} failed={failed} exit={proc.returncode}")

        executed = sum(r["executed"] for r in results)
        passed_total = sum(r["passed"] for r in results)
        failed_total = sum(r["failed"] for r in results)
        status = "passed" if executed == 15 and failed_total == 0 and all(r["ok"] for r in results) else "failed"
        upstream = {
            "status": status,
            "framework": "unity",
            "command": "cmake -S lwrb/test -B build/upstream-test && cmake --build build/upstream-test && ./lwrb_test && ./lwrb_test_ex",
            "discovered": 15,
            "executed": executed,
            "passed": passed_total,
            "failed": failed_total,
            "skipped": 0,
            "suites": results,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if status != "passed":
            for r in results:
                self.output.error(f"=== {r['exe']} tail ===\n{r['tail']}")
            raise RuntimeError("upstream tests failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lwrb"]
        self.cpp_info.set_property("cmake_file_name", "lwrb")
        self.cpp_info.set_property("cmake_target_name", "lwrb::lwrb")
