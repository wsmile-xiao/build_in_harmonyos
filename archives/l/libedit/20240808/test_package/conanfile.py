#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libedit/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibeditTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # HarmonyOS: create libtinfo.so symlink for test_package linking
        if self.settings.os in ("Linux", "OHOS"):
            lib_dir = os.path.join(self.build_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            tinfo_link = os.path.join(lib_dir, "libtinfo.so")
            if not os.path.exists(tinfo_link):
                try:
                    os.symlink("/usr/lib/libtinfo.so.6", tinfo_link)
                except OSError:
                    pass
            # Add to LDFLAGS so CMakeToolchain/CMake can find libtinfo.so
            current = os.environ.get("LDFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{lib_dir} {current}".strip()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Explicitly set LD_LIBRARY_PATH for libedit shared library
        libedit_info = self.dependencies["libedit"].cpp_info.aggregated_components()
        libdir = libedit_info.libdirs[0] if libedit_info.libdirs else ""
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_libedit")
        self.run(f"LD_LIBRARY_PATH={libdir} {test_exe}", env="conanrun")
