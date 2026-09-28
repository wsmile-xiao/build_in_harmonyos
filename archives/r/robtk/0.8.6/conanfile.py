#!/usr/bin/env python3
"""Conan 2 recipe for robtk 0.8.6 (HarmonyOS / OpenHarmony port).

robtk ("robin's LV2 UI tool kit") is not a library in the usual sense: it is a
*source toolkit* that downstream LV2 plugin projects compile into their UI
shared objects (`RW=<robtk dir>`, `#include "robtk.h"`, `$(RW)ui_gl.c`).
The package therefore ships the complete toolkit (headers, sources and the
upstream `robtk.mk`) and exposes include paths, compiler definitions and
system libraries so that a consumer can build the UI directly.

HarmonyOS adaptation (see patches/): HarmonyOS has no X11/GLX and no desktop
OpenGL. A new pugl backend (pugl/pugl_ohos.c) drives EGL + OpenGL ES 3 with a
OHNativeWindow provided by the host application, and the fixed-function GL
presentation of ui_gl.c is replaced by an OpenGL ES blit program
(gl/gles_present.h). The backend also supports offscreen rendering (EGL
pbuffer), which is what the test_package uses on a headless worker.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RobtkConan(ConanFile):
    name = "robtk"
    version = "0.8.6"
    description = ("LV2 UI toolkit (cairo/pango widgets, GTK+ and OpenGL ES "
                   "backends) with a native HarmonyOS OpenGL ES backend")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/x42/robtk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Source toolkit: consumers compile the sources, nothing is compiled here,
    # so the package carries headers/sources only (no library, no shared option).
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # robtk.h pulls in cairo + pango (widget rendering) and the LV2 headers
        # (UI/atom/urid/options).  Headers of these dependencies are part of the
        # public interface of robtk.h, so they must be transitive.
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("lv2/1.18.11-git", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "robtk is packaged for Linux and OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No compilation: the toolkit is compiled by its consumers.  The
        # HarmonyOS backend is added by the patches declared in conandata.yml.
        apply_conandata_patches(self)

    def package(self):
        dst = os.path.join(self.package_folder, "include", "robtk")
        copy(self, "*.h", src=self.source_folder, dst=dst)
        copy(self, "*.c", src=self.source_folder, dst=dst)
        copy(self, "*.mm", src=self.source_folder, dst=dst)
        copy(self, "*.cpp", src=self.source_folder, dst=dst)
        copy(self, "*.mk", src=self.source_folder, dst=dst)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=dst, keep_path=False)

    def package_id(self):
        # Only sources and headers are packaged: one package for all settings.
        self.info.clear()

    def package_info(self):
        # Upstream usage is `RW=<robtk dir>` with includes relative to the
        # toolkit root ("robtk.h", "pugl/pugl.h", "widgets/..."), so both the
        # include root and the toolkit root are exported.
        self.cpp_info.includedirs = ["include/robtk"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

        self.cpp_info.set_property("cmake_file_name", "robtk")
        self.cpp_info.set_property("cmake_target_name", "robtk::robtk")
        self.cpp_info.set_property("pkg_config_name", "robtk")

        if str(self.settings.os) == "OHOS":
            # HarmonyOS/OpenGL ES backend: EGL + OpenGL ES 3 + native window
            self.cpp_info.defines = ["RTK_GLES"]
            self.cpp_info.system_libs = [
                "EGL", "GLESv3", "native_window", "m", "pthread",
            ]
        else:
            self.cpp_info.system_libs = ["m", "pthread"]
