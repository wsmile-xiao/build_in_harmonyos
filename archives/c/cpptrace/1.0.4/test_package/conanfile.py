#!/usr/bin/env python3
"""Conan test_package for cpptrace 1.0.4.

Consumer-perspective verification: link the packaged library, exercise the
object API (frame rendering, version macros) and run a real stack trace
with symbol resolution on the OHOS runtime.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _sdk_llvm_lib_dir(self):
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(llvm_lib):
            return llvm_lib
        candidates = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        return candidates[0] if candidates else None

    def test(self):
        # The test executables link libc++_shared.so from the OHOS toolchain
        # and libzstd.so.1 from the Conan zstd package. musl has no rpath
        # support, so the loader needs explicit LD_LIBRARY_PATH entries:
        # env="conanrun" provides the Conan dependency run paths
        # (VirtualRunEnv), and the toolchain lib dir is prepended inline
        # (repo-wide test_package precedent: atk, c10t, akonadi).
        bindir = self.cpp.build.bindirs[0]
        env_prefix = ""
        if self.settings.os == "OHOS":
            llvm_lib = self._sdk_llvm_lib_dir()
            if llvm_lib:
                env_prefix = f"LD_LIBRARY_PATH={llvm_lib}/aarch64-linux-ohos:$LD_LIBRARY_PATH "

        for exe_name in ("test_package", "test_cpptrace_ohos"):
            exe = os.path.join(bindir, exe_name)
            if not os.path.isfile(exe):
                raise ConanException(f"test executable not found: {exe}")
            self.run(f'{env_prefix}"{exe}"', env="conanrun", cwd=self.build_folder)
