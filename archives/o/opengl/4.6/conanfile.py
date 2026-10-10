#!/usr/bin/env python3
"""Conan recipe — opengl 4.6 (Khronos OpenGL / OpenGL ES API headers).

Header-only package built from the official Khronos OpenGL-Registry
(main-branch snapshot pinned by SHA-256). Installs the api/ header tree
(GL 4.6 core+extensions, GLX/WGL, GLES 1/2/3, GLSC, GLSC2, KHR) as
include/GL, include/GLES, include/GLES2, include/GLES3, include/GLSC,
include/GLSC2 and include/KHR.

Upstream gap: the current OpenGL-Registry main snapshot no longer ships
api/KHR/khrplatform.h, while every GL/GLES/GLSC header #includes
<KHR/khrplatform.h>; the official Khronos khrplatform.h (from
EGL-Registry, MIT) is vendored in by patches/0001-add-khrplatform.h.patch.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class OpenglConan(ConanFile):
    name = "opengl"
    version = "4.6"
    description = "Khronos OpenGL 4.6 / OpenGL ES 1-3 / GLSC API headers (OpenGL-Registry)"
    license = "MIT"
    homepage = "https://github.com/KhronosGroup/OpenGL-Registry"
    url = "https://github.com/KhronosGroup/OpenGL-Registry"

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译: 仅应用补丁 (引入官方 khrplatform.h)
        apply_conandata_patches(self)

    def package(self):
        # api/ 整树 → include/ (GL/GLES/GLES2/GLES3/GLSC/GLSC2/KHR)
        shutil.copytree(
            os.path.join(self.source_folder, "api"),
            os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "opengl")
        self.cpp_info.set_property("cmake_target_name", "opengl::opengl")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
