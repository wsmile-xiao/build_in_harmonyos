#!/usr/bin/env python3
"""Conan test_package — libportal 0.10.0 L1 test.

Compiles and runs a C program that calls the real libportal Xdp* API
(portal type system, flatpak/sandbox probes, initable_new no-bus failure
path, settings object + signal lookup, notification GVariant building and
the mkenums-generated enum types), verifying headers, linking and runtime
behaviour without requiring a session D-Bus or a portal daemon.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibportalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def _build_environment(self):
        # Same whitespace-corrupted "/system/lib64" entry workaround as the
        # main recipe: prepend a clean /system/lib64 so host tools (cmake,
        # ninja) can resolve libc++_shared.so inside the conan build env.
        environment = Environment()
        if self.settings.os == "OHOS" and os.path.isdir("/system/lib64"):
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return environment

    def build(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libportal" + suffix)
        # run with the same clean-LD_LIBRARY_PATH workaround (the conanrun
        # env inherits the whitespace-corrupted session path)
        with self._build_environment().vars(self).apply():
            self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
