#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class IrrlichtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "test_irrlicht.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindir, "test_irrlicht")
            # conan's VirtualRunEnv injects deps' lib dirs into LD_LIBRARY_PATH
            # but not the just-built package's own; test_irrlicht links
            # libIrrlicht.so.1.8 (soname) which lives in the irrlicht
            # package's lib dir, so add that dir explicitly for the run.
            irrlicht_info = self.dependencies[self.tested_reference_str]
            libdirs = irrlicht_info.cpp_info.libdirs
            irrlicht_libdir = libdirs[0] if libdirs else "lib"
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                f"{irrlicht_libdir}:{existing}" if existing else irrlicht_libdir
            )
            try:
                self.run(exe, env="conanrun")
            finally:
                if existing:
                    os.environ["LD_LIBRARY_PATH"] = existing
                else:
                    os.environ.pop("LD_LIBRARY_PATH", None)
