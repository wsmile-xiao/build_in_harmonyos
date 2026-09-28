#!/usr/bin/env python3
"""Conan test_package for robtk 0.8.6 (HarmonyOS / OpenHarmony port).

The toolkit is consumed the way upstream intends: the consumer compiles
ui_gl.c (with its own UI source as PLUGIN_SOURCE) together with the platform
backend, here pugl/pugl_ohos.c.  Both test executables then run for real:

* test_pugl_ohos - the HarmonyOS/EGL backend itself: offscreen EGL pbuffer,
  OpenGL ES context, input bridge, frame read-back, resize, hide/show;
* test_robtk_ui   - the full UI stack: LV2 UI entry point of the toolkit,
  widget tree, cairo/pango rendering through OpenGL ES, pointer input.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class RobtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "cross-building: compile/link consumer test completed; "
                "execution is left to native OHOS CI"
            )
            return

        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_pugl_ohos", "test_robtk_ui"):
            self.run(os.path.join(bindir, exe), env="conanrun")
