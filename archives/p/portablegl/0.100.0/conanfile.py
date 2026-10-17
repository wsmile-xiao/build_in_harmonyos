#!/usr/bin/env python3
"""Conan recipe — portablegl 0.100.0 (header-only).

PortableGL: OpenGL 3.x core subset implemented in portable C99 as a
single-header library (stb style). Pure software rasterizer — no GPU,
no window-system dependency, zero third-party dependencies (libc + libm).

Usage in consumer code:
    #define PORTABLEGL_IMPLEMENTATION   // in exactly ONE translation unit
    #include "portablegl.h"

The public header is fully self-contained (all implementation is inlined
behind PORTABLEGL_IMPLEMENTATION; upstream src/ is the development source
for the header, not a build input).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class PortableglConan(ConanFile):
    name = "portablegl"
    version = "0.100.0"
    package_type = "header-library"

    description = (
        "PortableGL - OpenGL 3.x core subset software rasterizer as a "
        "portable C99 single-header library (stb style, MIT)"
    )
    homepage = "https://github.com/rswinkle/PortableGL"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # header-library: no binary artifact, settings only constrain consumers
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        # standard conan-center structure; no patches for 0.100.0,
        # kept so conandata patch declarations (if ever added) are exported
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        # header-only: every configuration yields the same headers
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # header-only library: nothing to compile here; consumers compile
        # the implementation via PORTABLEGL_IMPLEMENTATION. Rendering is
        # verified by test_package (offline framebuffer pixel assertions).
        # standard structure: apply conandata-declared patches (none now)
        apply_conandata_patches(self)

    def package(self):
        copy(self, "portablegl.h",
             src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "portablegl")
        self.cpp_info.set_property("cmake_target_name", "portablegl::portablegl")
        self.cpp_info.includedirs = ["include"]
