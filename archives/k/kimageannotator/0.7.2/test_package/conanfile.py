#!/usr/bin/env python3
"""Consumer test for kimageannotator (kImageAnnotator-Qt6) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KImageAnnotatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase uses cmake_find_mode "none" (relocatable Qt6Config.cmake);
        # Qt6Svg lives in the qtsvg package; kImageAnnotator-Qt6_DIR points
        # at the tested package's exported CMake config. This simulates the
        # real downstream consumption (ksnip/flameshot style):
        #   find_package(kImageAnnotator-Qt6 0.7.2 REQUIRED)
        #   target_link_libraries(... kImageAnnotator::kImageAnnotator)
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        qtsvg_prefix = self.dependencies["qtsvg"].package_folder
        kia_prefix = self.dependencies["kimageannotator"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6")
        tc.cache_variables["Qt6Widgets_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6Widgets")
        tc.cache_variables["Qt6Svg_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6Svg")
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qtsvg_prefix
        tc.cache_variables["kImageAnnotator-Qt6_DIR"] = os.path.join(
            kia_prefix, "lib", "cmake", "kImageAnnotator-Qt6")
        # Same platform-module fix as the library build: without
        # Platform/HarmonyOS.cmake the UNIX variable stays undefined and
        # FindX11's entire body is guarded by if(UNIX) -- it silently does
        # nothing, so find_package(X11 REQUIRED) would not define X11::X11.
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6", "platforms")
        # The test probes the library's X11 adaptation point directly
        # (includes <X11/Xlib.h>), so FindX11 must resolve against the same
        # conan packages as the library build (libx11 + xorgproto headers).
        x11_pkg = self.dependencies["libx11"].package_folder
        xproto_pkg = self.dependencies["xorgproto"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = x11_pkg
        tc.cache_variables["X11_X11_INCLUDE_PATH"] = os.path.join(
            x11_pkg, "include") + ";" + os.path.join(xproto_pkg, "include")
        tc.cache_variables["X11_X11_LIB"] = os.path.join(
            x11_pkg, "lib", "libX11.so")
        # Runtime closure note (E135): CMake has no HarmonyOS platform module,
        # so the link line carries no -rpath and the device default loader
        # path has no Qt/conan libraries. test() runs with env="conanrun"
        # (Conan writes every dependency libdir into LD_LIBRARY_PATH there;
        # kcolorpicker/0.3.1 and karchive/6.19.0 same-device precedent),
        # resolving libQt6*.so.6, libkColorPicker.so (PRIVATE DT_NEEDED of
        # libkImageAnnotator.so) and libX11.so.6.
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "kimageannotator test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_kimageannotator")
            # offscreen QPA + system font dir: qtbase ships no fonts and the
            # offscreen font database would be empty, crashing text rendering
            # inside the annotation widgets (same env as the upstream ctest
            # run in the library build()).
            prefix = "QT_QPA_PLATFORM=offscreen"
            if os.path.isdir("/system/fonts"):
                prefix += " QT_QPA_FONTDIR=/system/fonts"
            self.run(
                f'{prefix} "{executable}"', env="conanrun", ignore_errors=False)
