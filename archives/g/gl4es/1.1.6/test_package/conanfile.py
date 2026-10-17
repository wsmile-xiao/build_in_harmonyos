#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: run the offscreen render test (test.c creates an EGL pbuffer GLES2
        # context, draws a fixed-pipeline triangle via gl4es, and reads pixels back).
        # The test_package builds in-source (no cmake_layout), so the binary is at
        # <build_folder>/test_gl4es. LD_LIBRARY_PATH must include the gl4es package
        # libdir (libGL.so.1) AND /system/lib64 (real libEGL.so + libGLESv3.so).
        # LIBGL_* point gl4es at the OHOS GLES3/EGL system libs.
        test_bin = os.path.join(self.build_folder, "test_gl4es")
        deps = self.dependencies["gl4es"]
        gl_lib = ":".join(os.path.join(deps.package_folder, d) for d in deps.cpp_info.libdirs)
        ld = ":".join(intd for intd in [gl_lib, "/system/lib64", os.environ.get("LD_LIBRARY_PATH", "")] if intd)
        self.run("LD_LIBRARY_PATH=%s LIBGL_GLES=/system/lib64/libGLESv3.so "
                 "LIBGL_EGL=/system/lib64/libEGL.so %s" % (ld, test_bin))
