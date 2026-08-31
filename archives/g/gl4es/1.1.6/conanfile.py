#!/usr/bin/env python3
"""Conan recipe for gl4es 1.1.6 — desktop OpenGL-over-GLES2 compatibility layer.

gl4es translates OpenGL 1.5/2.1 fixed-pipeline/legacy calls to OpenGL ES 2.0/1.1
(FPE fixed-pipeline emulator), so desktop-OpenGL-only C/C++ software/games can run
on OpenHarmony PC (which ships only OpenGL ES 3.2 + EGL, NO desktop libGL).

OHOS notes:
- Build with `-DNOX11=ON` (no X11 backend; OHOS has no X11) and `-DDEFAULT_ES=2`
  (GLES2 backend, backward-compatible with the GLES3 hardware context).
- Produces `libGL.so` (provides `-lGL`) + GL headers. Consumers set
  `LIBGL_GLES=/system/lib64/libGLESv3.so` & `LIBGL_EGL=/system/lib64/libEGL.so`
  at runtime (OHOS has no libGLESv2.so, only libGLESv3.so).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Gl4esConan(ConanFile):
    name = "gl4es"
    version = "1.1.6"
    description = "OpenGL 1.5/2.1 -> GLES 2.0/1.1 translation library (desktop GL compat layer)"
    license = "MIT"
    homepage = "https://github.com/ptitseb/gl4es"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No extra conan dependencies; runtime GLES/EGL libs are system-provided.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: cmake reports "System is unknown (HarmonyOS)" — harmless; NOX11 avoids X11.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["NOX11"] = "ON"
        tc.cache_variables["NOEGL"] = "OFF"
        tc.cache_variables["DEFAULT_ES"] = "2"
        tc.cache_variables["STATICLIB"] = "OFF" if self.options.shared else "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # R: patch bumps cmake_minimum_required to 3.5; also set the policy floor for cmake 4.x.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        # gl4es has no CMake install; CMAKE_LIBRARY_OUTPUT_DIRECTORY=${CMAKE_SOURCE_DIR}/lib,
        # and in a conan build CMAKE_SOURCE_DIR == build_folder (source copied there).
        dst_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(dst_lib, exist_ok=True)
        copy(self, "libGL.so*", src=os.path.join(self.build_folder, "lib"), dst=dst_lib, keep_path=False)
        copy(self, "libGL.so*", src=os.path.join(self.source_folder, "lib"), dst=dst_lib, keep_path=False)
        # Provide libGL.so (CMakeDeps find_library("GL") resolves it), symlink -> libGL.so.1
        gl1 = os.path.join(dst_lib, "libGL.so.1")
        gl0 = os.path.join(dst_lib, "libGL.so")
        if os.path.isfile(gl1) and not os.path.exists(gl0):
            os.symlink(os.path.basename(gl1), gl0)
        copy(self, "*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["GL"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
