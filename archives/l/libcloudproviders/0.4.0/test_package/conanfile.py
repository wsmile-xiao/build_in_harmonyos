#!/usr/bin/env python3
"""Conan test_package — libcloudproviders 0.4.0 L1 test.

Compiles and runs a C program that calls the real libcloudproviders API:
GType registration checks (Collector/Account/Provider/Exporter), collector
singleton creation + type consistency, public ABI enum values, and (when a
session bus is available) the provider/account exporter set/get round-trips.
OHOS has no dbus-daemon, so exporter assertions auto-skip and print the
platform limitation while the type/singleton/enum assertions always run.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibcloudprovidersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test source also uses glib-2.0 / gio-2.0 (g_print / g_bus_get_sync)
        self.requires("glib/2.88.3.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libcloudproviders" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
