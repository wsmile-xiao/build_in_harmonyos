#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        # The tested package (mupdf-gl): the test compiles the package's own
        # patched platform/gl/gl-ui.c (shipped under include/mupdf-gl-ohos/)
        # and drives ui_draw_image() end-to-end — a substantive dependency on
        # the tested package, not a shell test (R34).
        self.requires(self.tested_reference_str)
        # freeglut headers (GL/freeglut.h) are pulled in transitively by
        # gl-app.h; the OHOS-adapted freeglut 3.6.0 is published in the
        # registry. The test needs its include dir to compile gl-ui.c.
        self.requires("freeglut/3.6.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindir = self.cpp.build.bindirs[0]
            self.run(os.path.join(bindir, "test_vao"), env=["conanrun"])
