#!/usr/bin/env python3
"""Conan test_package — libfm-qt.

Compiles upstream test files (src/tests/) plus our test.cpp.
Upstream tests require QApplication; use QT_QPA_PLATFORM=offscreen
to run without a display server.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain


class LibfmqtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        cmake_deps = CMakeDeps(self)
        tc = CMakeToolchain(self)
        if "qtbase" in self.dependencies.host:
            # qtbase has cmake_find_mode="none" (it ships its own Qt6 cmake
            # configs); declare it here too so CMakeDeps skips emitting a
            # qtbase config. However libfm-qt-config.cmake may still contain
            # find_dependency(qtbase) — provide a stub qtbase config so that
            # call resolves successfully. Real Qt6 modules stay reachable via
            # the Qt6_DIR variables below.
            cmake_deps.set_property("qtbase", "cmake_find_mode", "none")
            qtbase_stub = os.path.join(self.generators_folder, "qtbase-stub")
            os.makedirs(qtbase_stub, exist_ok=True)
            cfg = os.path.join(qtbase_stub, "qtbaseConfig.cmake")
            if not os.path.exists(cfg):
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(
                        "# Stub qtbase config (qtbase uses cmake_find_mode=none;\n"
                        "# real Qt6 modules are found via Qt6_DIR).\n"
                        "set(qtbase_FOUND TRUE)\n"
                        "set(qtbase_VERSION 6.11.1)\n"
                        "# CMakeDeps puts qtbase::qtbase into libfm-qt_DEPS_TARGET;\n"
                        "# provide a no-op imported target so that resolves.\n"
                        "if(NOT TARGET qtbase::qtbase)\n"
                        "  add_library(qtbase::qtbase INTERFACE IMPORTED)\n"
                        "endif()\n"
                    )
            tc.variables["qtbase_DIR"] = qtbase_stub
            qtbase_cmake = os.path.join(
                self.dependencies.host["qtbase"].package_folder,
                "lib", "cmake"
            )
            if os.path.isdir(qtbase_cmake):
                tc.variables["Qt6_DIR"] = os.path.join(qtbase_cmake, "Qt6")
                tc.variables["Qt6Widgets_DIR"] = os.path.join(qtbase_cmake, "Qt6Widgets")
                tc.variables["Qt6Gui_DIR"] = os.path.join(qtbase_cmake, "Qt6Gui")
        if "glib" in self.dependencies.host:
            # libfm-qt6 public headers (core/folder.h, core/gobjectptr.h,
            # core/volumemanager.h) include <glib.h>/<gio/gio.h>. The glib
            # CMakeDeps component include dirs do not cover gio-unix-2.0 (or the
            # top-level include for libintl.h), so mirror the main recipe's GLIB
            # include injection for the test targets.
            g = self.dependencies.host["glib"].package_folder
            tc.variables["GLIB_INCLUDE_DIRS"] = ";".join([
                os.path.join(g, "include", "glib-2.0"),
                os.path.join(g, "lib", "glib-2.0", "include"),
                os.path.join(g, "include"),
                os.path.join(g, "include", "gio-unix-2.0"),
            ])
            tc.variables["GLIB_GIO_UNIX_INCLUDE_DIR"] = os.path.join(g, "include", "gio-unix-2.0")
        cmake_deps.generate()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run tests with offscreen platform (no display needed)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        # L0d gate requires a self.run() call; run the upstream folder test.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test-folder")
        self.run(test_bin, env="conanrun")
        # Run all registered tests (5 upstream + test_libfm-qt) via ctest
        cmake = CMake(self)
        cmake.test()
