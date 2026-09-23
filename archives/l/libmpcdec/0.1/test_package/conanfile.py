#!/usr/bin/env python3
"""Consumer test for the packaged libmpcdec.

Builds test_libmpcdec.c against the installed library (CMakeDeps) and runs it;
the program decodes an embedded MusePack SV8 stream through the public decoder
API and asserts the parsed stream header plus the decoded PCM.

File location: archives/l/libmpcdec/0.1/test_package/conanfile.py
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibmpcdecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test_libmpcdec.c", "fixture_mpc.h"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException(
                "test executable directory is unavailable: "
                "cmake_layout() did not define self.cpp.build.bindirs"
            )
        self.run("./test_libmpcdec", env="conanrun", cwd=bindirs[0])
