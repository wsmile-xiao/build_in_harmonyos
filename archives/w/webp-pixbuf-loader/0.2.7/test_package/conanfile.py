#!/usr/bin/env python3
"""Consumer test for webp-pixbuf-loader 0.2.7.

This test exercises the pixbufloader-webp shared module by loading it
with dlopen and calling its fill_info() entry point to verify the
module is correctly built and exports the expected GDK Pixbuf loader
interface.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WebpPixbufLoaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_binary = os.path.join(
            self.cpp.build.bindirs[0], "test_webp_pixbuf_loader"
        )
        if can_run(self):
            dep = self.dependencies["webp-pixbuf-loader"]
            pkg_folder = dep.package_folder
            # The module is installed at lib/gdk-pixbuf-2.0/loaders/
            module_dir = os.path.join(
                pkg_folder, "lib", "gdk-pixbuf-2.0", "loaders"
            )
            # Set env vars so the test binary can find the .so module
            self.run(
                f'WEBP_PIXBUF_LOADER_ROOT="{pkg_folder}" '
                f'WEBP_PIXBUF_LOADER_MODULE_DIR="{module_dir}" '
                f'"{test_binary}"',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross-building: consumer binary is run on OHOS device"
            )
