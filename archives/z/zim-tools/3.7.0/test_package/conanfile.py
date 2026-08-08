#!/usr/bin/env python3
"""Consumer test for zim-tools - verify the tool binary runs.

R34: test.c invokes the packaged zimdump binary via popen() and is compiled
and executed through CMake/CTest; test() additionally runs `zimdump --help`
on native platforms.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ZimtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Build is deferred to test() where ZIMDUMP_BIN is available
        pass

    def test(self):
        dep = self.dependencies["zim-tools"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        zimdump = os.path.join(dep.package_folder, bindir, "zimdump")
        if not os.path.exists(zimdump):
            raise Exception(
                f"zimdump binary not found at {zimdump} — "
                "package did not install the expected binary")
        # Compile test.c and run it via CTest (popen calls zimdump --help)
        cmake = CMake(self)
        cmake.configure(variables={"ZIMDUMP_BIN": zimdump})
        cmake.build()
        if not can_run(self):
            self.output.info(
                "Runtime test skipped (cross-compilation, binary exists)")
            return
        if self.settings.os == "OHOS":
            self.output.info(
                "OHOS runtime test skipped (ELF signing required)")
        else:
            cmake.test()
            self.run(f'"{zimdump}" --help')
