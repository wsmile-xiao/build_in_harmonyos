#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/SDL2/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Sdl2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        import os
        import shutil
        bindir = self.cpp.build.bindirs[0]
        # OpenHarmony's musl ld does not search the executable's directory for
        # shared libs by default. For shared builds, copy the shared libs next
        # to the test binary and set LD_LIBRARY_PATH so the dynamic linker can
        # resolve them.
        dep = self.dependencies[self.tested_reference_str]
        if dep.package_folder:
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                for f in os.listdir(libdir):
                    if ".so" in f:
                        src = os.path.join(libdir, f)
                        dst = os.path.join(bindir, f)
                        if os.path.isfile(src) and not os.path.exists(dst):
                            shutil.copy2(src, dst)
        os.environ["LD_LIBRARY_PATH"] = bindir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_SDL2')}", env="conanrun")
