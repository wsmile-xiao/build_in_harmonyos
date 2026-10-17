#!/usr/bin/env python3
"""Conan test_package — lxqt-menu-data (pure data package).

The package installs data files only; the test verifies that the
expected menu definitions and desktop-directories were installed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain


class LxqtmenudataTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # Pass the installed share/ directory to test.c so it can verify
        # data files (R34: test must actually validate the package).
        pkg = self.dependencies["lxqt-menu-data"]
        data_dir = os.path.join(pkg.package_folder, "share")
        cmake.configure(variables={"MENU_DATA_DIR": data_dir})
        cmake.build()

    def test(self):
        # Also verify data files directly from the package folder
        pkg = self.dependencies["lxqt-menu-data"]
        share = os.path.join(pkg.package_folder, "share")
        menus = os.path.join(share, "menus")
        ddirs = os.path.join(share, "desktop-directories")

        for f in ("lxqt-applications.menu",
                  "lxqt-applications-compact.menu",
                  "lxqt-applications-fm.menu",
                  "lxqt-config.menu",
                  "lxqt-panel-applications.menu"):
            path = os.path.join(menus, f)
            if not os.path.isfile(path):
                raise Exception(f"missing menu file: {path}")
        self.output.info("menu files present")

        if not os.path.isdir(ddirs):
            raise Exception(f"missing desktop-directories dir: {ddirs}")
        dd_files = os.listdir(ddirs)
        if len(dd_files) < 20:
            raise Exception(f"too few desktop-directory files: {len(dd_files)}")
        self.output.info(f"desktop-directories present: {len(dd_files)} files")

        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lxqt-menu-data"),
                 env="conanrun")