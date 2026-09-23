#!/usr/bin/env python3
"""Conan test_package — Coin3D L1 consumer test.

Consumer program is built and executed via conan create (CI runs this
automatically). test.cpp exercises the public scene-graph API headlessly.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Coin3DTestConan(ConanFile):
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
        # musl's loader ignores DT_RUNPATH and conan 2 injects no rpath into
        # the consumer binary, so the runtime search path must be provided
        # explicitly: aggregate every (transitive) dependency's package lib
        # directory into LD_LIBRARY_PATH.
        import os
        bindir = os.path.abspath(self.cpp.build.bindirs[0])
        libdirs = [bindir]
        for name in ("coin3d", "mesa", "freetype", "zlib", "bzip2", "openal",
                     "expat"):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            if getattr(dep, "package_folder", None):
                libdirs.append(os.path.join(dep.package_folder, "lib"))
        self.run('LD_LIBRARY_PATH="%s" "%s/test_coin3d"' % (
            ":".join(libdirs), bindir))
