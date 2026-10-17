#!/usr/bin/env python3
"""Conan test_package — boost1.84-log 1.84.0 L1 functional test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoostLogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct require on the meta-package: the test sources include boost
        # headers, and CMakeDeps only generates full component variables for
        # direct requires (transitive-only deps get empty INCLUDE_DIRS on this
        # Conan build, verified experimentally).
        self.requires("boost/1.84.0")

    def layout(self):
        cmake_layout(self)

    def _cxx_executable(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp", "clang++")

    def _sdk_llvm_libdir(self):
        """Locate the OHOS SDK directory that provides libc++_shared.so
        (needed at runtime by the cross-compiled test binary on the build
        host). The shared libc++ lives under llvm/lib/aarch64-linux-ohos/."""
        if str(self.settings.os) != "OHOS":
            return ""
        cxx = self._cxx_executable()
        cxx = os.path.realpath(cxx)
        llvm_root = os.path.dirname(os.path.dirname(cxx))
        candidates = [
            os.path.join(llvm_root, "lib", "aarch64-linux-ohos"),
            os.path.join(llvm_root, "lib", "aarch64-linux-ohos", "c++"),
            os.path.join(llvm_root, "lib"),
        ]
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "libc++_shared.so")):
                return candidate
        return ""

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d 门禁要求 test() 中存在显式 self.run() 调用（R34）。
        # The test binary links libc++_shared.so from the OHOS SDK; prepend
        # the SDK llvm/lib to LD_LIBRARY_PATH so it resolves at runtime.
        # (CTest/cmake.test() does not inherit runtime lib paths, so the test
        # executable is executed directly via self.run() — this is the actual
        # pass/fail gate; ctest would run the very same binary.)
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.run(
                f"LD_LIBRARY_PATH={sdk_llvm_lib}:$LD_LIBRARY_PATH "
                f"{os.path.join(self.cpp.build.bindirs[0], 'test_boost_log')}"
            )
        else:
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_boost_log"))
