#!/usr/bin/env python3
"""Conan recipe for zdbsp 1.19-20181027-dfsg.1 — ZDoom standalone node builder.

ZDBSP builds BSP (and GL-friendly) nodes for Doom-format WAD files. It is a
single command-line executable, built with CMake, and needs zlib at link time.

OHOS adaptations (patch 0001, portability):
  1. cmake_minimum_required 2.4 -> 3.5: CMake 4.x hard-errors on projects
     declaring a minimum below 3.5.
  2. Link system zlib through the imported target ZLIB::ZLIB: the old
     CMakeLists relied on the legacy ZLIB_LIBRARIES / ZLIB_INCLUDE_DIR
     variables, which Conan CMakeDeps does not populate, so linking and
     include discovery would silently fail on OHOS.

Notes:
  - aarch64 builds automatically define -DDISABLE_SSE (CMakeLists checks
    CMAKE_SIZEOF_VOID_P == 4), so no SSE code is compiled on HarmonyOS PC.
  - stricmp/strnicmp are absent from the OHOS libc; the CMake
    CHECK_FUNCTION_EXISTS probe defines -Dstricmp=strcasecmp and
    -Dstrnicmp=strncasecmp automatically (same path as macOS/glibc-free libcs).
  - The bundled zlib/ subdirectory only contains the compression half (no
    inflate sources), so the system zlib from ohpcd must be used (patch makes
    the imported target mandatory).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class ZdbspConan(ConanFile):
    name = "zdbsp"
    version = "1.19-20181027-dfsg.1"
    description = "ZDoom 独立节点构建器 — 为 Doom 格式 WAD 构建 BSP/GL 节点"
    license = "GPL-2.0"
    homepage = "https://github.com/rheit/zdbsp"
    url = "https://github.com/rheit/zdbsp"

    # Command-line tool, not a library (R38: commands.json at software level)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib is published on ohpcd (archives/z/zlib/1.3.1, static build per R26)
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: OHOS must be treated as a Linux-like platform
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zdbsp is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # zlib recipe's default CMakeDeps target is zlib::zlib; the upstream
        # CMakeLists uses find_package(ZLIB) + ZLIB::ZLIB. Map the target name
        # so the patched CMakeLists links the Conan zlib on OHOS and the
        # system zlib locally (both provide ZLIB::ZLIB).
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream CMakeLists has no install() rule; copy the single binary.
        copy(self, "zdbsp", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
