#!/usr/bin/env python3
"""Conan test_package — libdumbtts.

The library reads pronunciation config from /usr/share/dumbtts/,
/etc/dumbtts/ then $HOME/.dumbtts_<lang>.conf; TTSInit("en") therefore
needs an en.conf reachable from $HOME. On CI the package's bundled
res/dumbtts/en.conf does not sit at those paths, so the test seeds a
copy into $HOME before running the binary.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdumbttsTestConan(ConanFile):
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
        dep = self.dependencies["libdumbtts"]
        conf_src = os.path.join(dep.package_folder, "res", "dumbtts", "en.conf")
        conf_dst = os.path.join(os.path.expanduser("~"), ".dumbtts_en.conf")
        if not os.path.isfile(conf_src):
            raise RuntimeError(f"bundled res/dumbtts/en.conf not found: {conf_src}")
        shutil.copyfile(conf_src, conf_dst)
        # Run the test binary directly (clearer than ctest for this case).
        bindir = os.path.join(self.cpp.build.bindirs[0]) if self.cpp.build.bindirs else "."
        bin_path = os.path.join(bindir, "test_libdumbtts")
        if not os.path.isfile(bin_path):
            # cmake_layout: build dir default
            bin_path = os.path.join(self.build_folder, "test_libdumbtts")
        self.run(bin_path, env="conanrun")