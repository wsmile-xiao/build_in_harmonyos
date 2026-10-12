#!/usr/bin/env python3
"""Conan test_package for qtxdg 3.12.0 (Qt5Xdg / libqtxdg) on OpenHarmony PC.

R34: the test genuinely depends on the tested package - the test source
compiles against the installed Qt5Xdg headers and links the installed
Qt5Xdg / Qt5XdgIconLoader archives, then calls the real XdgDirs /
XdgDesktopFile API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtxdgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt5 is also required directly so Conan's CMakeDeps exports the Qt5
        # include directories to this test (transitive component requires do
        # not carry the header paths).
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in list(dep.cpp_info.libdirs) or ["lib"]:
                full = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(full):
                    env.prepend_path("LD_LIBRARY_PATH", full)

        # The test creates a QTemporaryDir; /tmp is read-only on OHOS.
        tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        env.define("QT_QPA_PLATFORM", "offscreen")

        bindir = self.cpp.build.bindirs[0]
        executable = os.path.join(bindir, "test_qtxdg")
        with env.vars(self).apply():
            self.run(executable, cwd=bindir)
