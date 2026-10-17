#!/usr/bin/env python3
"""Conan recipe — opencsg 1.8.2 (CMake).

OpenCSG is an image-based (z-buffer) CSG rendering library for OpenGL.  It
bundles a privately generated copy of glad and resolves every OpenGL entry
point at runtime through dlopen(), so the library itself has no link-time GL
dependency.

HarmonyOS adaptation notes
--------------------------
* The renderer is portable C++17; the only platform-specific piece is the glad
  loader, which needs to know where HarmonyOS keeps its OpenGL entry points.
  HarmonyOS ships a desktop OpenGL entry library, ``libGLv4.so``, next to
  ``libEGL.so`` / ``libGLESv3.so``; ``eglGetProcAddress`` comes from
  ``libEGL.so``.  ``patches/0001-glad-ohos-opengl-loader.patch`` appends
  ``libGLv4.so`` to the loader's candidate names, and makes the proc-address
  helper fall back to ``eglGetProcAddress`` when GLX is unavailable.  Both are
  POSIX-generic changes guarded only by glad's own platform macros, so no
  platform macro is introduced (R8) and other platforms keep their behaviour.
* ``src/CMakeLists.txt`` calls ``find_package(OpenGL REQUIRED)`` even though the
  library target never links OpenGL (glad resolves it at runtime).  HarmonyOS
  has no OpenGL development package, so
  ``patches/0002-src-CMakeLists-optional-opengl-lookup.patch`` makes that lookup
  optional.  On platforms that do ship OpenGL the lookup still runs unchanged.
* No Conan dependency is required: the GL loader is resolved at runtime and the
  GL libraries are supplied by the device.
* The library is built with GPL-2.0-or-later (see copying.txt).

Upstream tests
--------------
OpenCSG 1.8.2 has no unit-test suite.  ``example/`` is the only test/sample
source and it is a GLUT window program that needs a real GL context, so it is
disabled (``BUILD_EXAMPLE=OFF``) and left to the device shadow CI.  The real
consumer test is ``test_package/`` (see ``test_package/MANIFEST.yml``).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"

# Explicit download filename so Conan's get() picks the tar.gz decompressor
# regardless of how the archive basename looks (see knowledge entry E276).
_SOURCE_FILENAME = "opencsg-1.8.2.tar.gz"


class OpencsgConan(ConanFile):
    name = "opencsg"
    version = "1.8.2"
    description = "Image-based CSG rendering library for OpenGL"
    license = "GPL-2.0-or-later"
    homepage = "http://www.opencsg.org"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename=_SOURCE_FILENAME,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        # The GLUT example needs a desktop window/GLUT; it is not part of the
        # packaged library and cannot build on the CI toolchain.
        tc.variables["BUILD_EXAMPLE"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "copying.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "gpl-*.txt",
            src=os.path.join(self.source_folder, "doc", "license"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenCSG")
        self.cpp_info.set_property("cmake_target_name", "OpenCSG::opencsg")
        self.cpp_info.libs = ["opencsg"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # glad dlopen()s the GL libraries itself, so there is no GL link
        # dependency; only the libc runtime loader is needed.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m"]
