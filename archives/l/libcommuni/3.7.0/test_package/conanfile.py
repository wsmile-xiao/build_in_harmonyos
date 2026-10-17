#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libcommuni/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibcommuniTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # libcommuni forwarding headers (<IrcCore/IrcConnection>) resolve
        # inner <ircglobal.h> against include/IrcCore; Qt headers come from
        # the qtbase package include dir
        inc = self.dependencies["libcommuni"].cpp_info.includedirs[0]
        # forwarding headers (<IrcCore/IrcConnection>) resolve inner
        # <ircglobal.h>-style includes against the module dirs themselves
        inc_dirs = [inc,
                    os.path.join(inc, "IrcCore"),
                    os.path.join(inc, "IrcModel"),
                    os.path.join(inc, "IrcUtil")]
        inc_dirs += self.dependencies["qt5-qtbase"].cpp_info.includedirs
        # static consumption of libcommuni requires IRC_STATIC (see libcommuni.pro)
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_FLAGS"] = "-DIRC_STATIC " + " ".join("-I%s" % p for p in inc_dirs)
        # static IrcCore still references Qt5Core.so.5 at runtime: embed the
        # qtbase libdir via RUNPATH (proven working on this platform)
        libdirs = [self.dependencies["libcommuni"].cpp_info.libdirs[0],
                   self.dependencies["qt5-qtbase"].cpp_info.libdirs[0]]
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,-rpath,%s" % ":".join(libdirs)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # keep run env usable for shared consumers too (default build is static)
        libdirs = [self.dependencies["libcommuni"].cpp_info.libdirs[0],
                   self.dependencies["qt5-qtbase"].cpp_info.libdirs[0]]
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libcommuni"),
                 env=["LD_LIBRARY_PATH=%s" % os.pathsep.join(libdirs)])
