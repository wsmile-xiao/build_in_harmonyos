#!/usr/bin/env python3
"""Conan recipe — cpu_features 0.11.0 (Google CPU features detection library).

CMake project.  Upstream test suite (GTest) is enabled and run in build();
the googletest source is NOT downloaded from GitHub at configure time (the
OHOS CI network cannot reach GitHub) — instead an external GoogleTest
provided by the Conan gtest package is used.  See patch
0001-CMakeLists.txt.patch which maps the bare gtest/gmock_main target names
onto the namespaced GTest::* targets exported by the Conan gtest package.

Upstream 0.9.0 -> 0.11.0 delta (audited for this version bump):
  * Public aarch64 API unchanged (GetAarch64Info /
    GetAarch64FeaturesEnumValue / GetAarch64FeaturesEnumName); new feature
    bits (mops/hbc/lse128/f8*/sme*/poe ...) and matching enum entries were
    appended — additive only, consumers of 0.9.0 build unchanged.
  * Test suite: 133 TEST/TEST_F declarations (0.9.0 had 132); the single
    addition is FreeBSD-only MrsMidrEl1_RPI4 which never instantiates on
    Linux/OHOS.
  * CMake: googletest download logic identical to 0.9.0 (patch 0001 still
    applies at a slightly shifted offset); CMAKE_CXX_STANDARD block moved
    into test/CMakeLists.txt via target_compile_features.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CpufeaturesConan(ConanFile):
    name = "cpu_features"
    version = "0.11.0"
    description = "A cross-platform C library to retrieve CPU features (such as CPUID) at runtime"
    license = "Apache-2.0"
    homepage = "https://github.com/google/cpu_features"
    url = "https://github.com/google/cpu_features"
    topics = ("cpu", "cpuid", "hardware", "detection", "c")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpu_features is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def build_requirements(self):
        # Upstream test suite links against gtest/gmock_main.
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake has no OHOS platform module; force the Linux branch so the
        # upstream code selects the Linux/Android aarch64 implementation.
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch))
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXECUTABLE"] = "ON"
        tc.variables["ENABLE_INSTALL"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        gtest = self.dependencies["gtest"]
        tc.variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream GTest suite and emit the HMBS_UPSTREAM_TEST_RESULT
        marker with the dual-tally accounting.

        Source audit (test/*.cc, tag v0.11.0): 133 TEST/TEST_F declarations
        across 9 test translation units; the architecture-specific suites
        (x86 69, arm 11, mips 7, ppc 5, s390x 4, riscv 5, loongarch 2) are
        mutually exclusive per PROCESSOR_IS_* CMake branch.
        On OHOS/armv8 the instantiated set is: bit_utils_test (2) +
        string_view_test (17) + stack_line_reader_test (4) +
        cpuinfo_aarch64_test (4, Linux branch) = 27.

        Upstream 0.11.0 builds the test executables into the `test/`
        subdirectory of the build folder (0.9.0 placed them in the build
        root), so both locations are probed.
        """
        candidates = [
            os.path.join(self.build_folder, "test"),
            os.path.join(self.build_folder, "bin"),
            self.build_folder,
        ]
        ctest = next((c for c in candidates if os.path.isfile(
            os.path.join(c, "bit_utils_test"))), candidates[0])
        # The OHOS clang target links libc++_shared.so from the SDK; add the
        # SDK lib dir so the test binaries can resolve their C++ runtime.
        run_env = dict(os.environ)
        sdk_hint = os.environ.get("OHOS_SDK_NATIVE",
                                  "/data/service/hnp/ohos-sdk.org/"
                                  "ohos-sdk_26.0.0.18/ohos/native")
        sdk_lib = os.path.join(sdk_hint, "llvm", "lib", "aarch64-linux-ohos")
        if os.path.isdir(sdk_lib):
            run_env["LD_LIBRARY_PATH"] = (
                sdk_lib + os.pathsep + run_env.get("LD_LIBRARY_PATH", ""))
        exes = ["bit_utils_test", "string_view_test",
                "stack_line_reader_test", "cpuinfo_aarch64_test"]
        passed = 0
        failed = 0
        discovered = 0
        commands = []
        for name in exes:
            exe = os.path.join(ctest, name)
            if not os.path.isfile(exe):
                self.output.warning(f"upstream test binary missing: {exe}")
                failed += 1
                continue
            commands.append(exe)
            try:
                result = subprocess.run(
                    [exe], cwd=ctest, capture_output=True, text=True,
                    timeout=1800, env=run_env)
            except subprocess.TimeoutExpired:
                self.output.error(f"{name} timed out")
                failed += 1
                continue
            out = (result.stdout or "") + (result.stderr or "")
            m = re.search(r"\[\s*PASSED\s*\] (\d+) tests?", out)
            n = int(m.group(1)) if m else 0
            mf = re.search(r"\[\s*FAILED\s*\] (\d+) tests?", out)
            nf = int(mf.group(1)) if mf else 0
            discovered += n + nf
            passed += n
            failed += nf
            self.output.info(
                f"{name} exit={result.returncode} passed={n} failed={nf}\n"
                + "\n".join(out.splitlines()[-8:]))

        status = "passed" if failed == 0 and discovered > 0 else (
            "failed" if failed > 0 else "no_tests")
        marker = {
            "status": status,
            "framework": "gtest",
            "command": " && ".join(commands),
            "source_declared_total": 133,
            "configured_executable_total": 27,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "note": "133 declared upstream tests; arch-specific suites are "
                    "mutually exclusive; 27 instantiated on OHOS/armv8",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cpu_features"]
