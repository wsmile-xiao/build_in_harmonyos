#!/usr/bin/env python3
"""Consumer test for libopenraw-pixbuf-loader 0.3.7.

Builds a small C program that dlopen()s the packaged gdk-pixbuf module
(libopenraw_pixbuf.so) and calls its fill_info()/fill_vtable() entry points,
verifying the RAW loader metadata and the incremental-load vtable wiring.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gdk-pixbuf headers are needed by the test to declare the exact
        # GdkPixbufFormat / GdkPixbufModule structs.
        self.requires("gdk-pixbuf/2.44.6")
        # keep zlib consistent with the package itself (boost vs glib pin)
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: consumer binary is run on the OHOS device"
            )
            return
        binary = os.path.join(
            self.cpp.build.bindirs[0], "test_openraw_pixbuf_loader"
        )
        dep = self.dependencies["libopenraw-pixbuf-loader"]
        module = os.path.join(
            dep.package_folder, "lib", "gdk-pixbuf-2.0", "loaders",
            "libopenraw_pixbuf.so",
        )
        self.run(
            f'OPENRAW_PIXBUF_MODULE="{module}" "{binary}"',
            env="conanrun",
        )
