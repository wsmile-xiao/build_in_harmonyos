#!/usr/bin/env python3
"""Conan test_package for filament 1.76.1.

Filament is a multi-library project: `conan create` installs the main
`filament` archive plus ~38 component archives under `lib/`.  The consumer
test links all of them (see CMakeLists.txt) and runs the engine on the noop
backend, which needs no GPU or window system.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain


class FilamentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # NOTE: CMakeToolchain must NOT also be listed in `generators`.  Conan 2
    # rejects a recipe that declares it there and instantiates it in
    # generate() as well:
    #
    #   ConanException: CMakeToolchain is declared in the generators
    #   attribute, but was instantiated in the generate() method too.
    #
    # The manual instantiation below is required -- it sets FILAMENT_PKG_DIR,
    # which test_package/CMakeLists.txt consumes -- so the attribute is the
    # one that goes.  The toolchain is still generated, exactly once.

    def configure(self):
        self.settings.compiler.cppstd = "20"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        dep = self.dependencies["filament"]
        pkg = dep.package_folder.replace("\\", "/")
        tc.variables["FILAMENT_PKG_DIR"] = pkg
        # Read the directory the recipe declares in package_info() rather than
        # assuming `lib/`: Filament installs to `lib/<DIST_DIR>`, so a hardcoded
        # `lib` globs an empty directory and the configure fails.  Taking it from
        # cpp_info also makes this configure assert that the package layout and
        # the declared libdir really do agree.
        #
        # `libdirs` is the official field; the singular `libdir` is a read-only
        # getter that raises unless the list holds exactly one element
        # (cpp_info.py:241-245).
        tc.variables["FILAMENT_PKG_LIBDIR"] = dep.cpp_info.libdirs[0].replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.test()
            # CI gate: test() must execute the consumer binary through a real
            # self.run() step, not only cmake.test().
            binary = os.path.join(self.cpp.build.bindirs[0], "test_filament")
            self.run(binary, env="conanrun")
