#!/usr/bin/env python3
"""Conan recipe for dirent 1.26 — portable dirent.h (tronkko/dirent).

dirent provides a Windows-compatible dirent.h for Microsoft Visual Studio;
on POSIX / HarmonyOS the system dirent.h is used.  Upstream ships a CMake
INTERFACE library `dirent` plus a CMake package config (DirentConfig.cmake),
installing the header under include/dirent-<version>/ and the config under
lib/cmake/Dirent-<version>/, so cross-platform consumers can
`find_package(Dirent)` and link the `dirent` target.

The package is header-only: nothing is compiled into the package itself.
Upstream unit tests (9 CTest entries) are enabled during build() so they are
compiled and executed against the platform dirent API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class DirentConan(ConanFile):
    name = "dirent"
    version = "1.26"
    description = ("dirent — a portable dirent.h that makes directory "
                   "navigation available on Windows for cross-platform "
                   "code; on POSIX/OHOS the system dirent API is used "
                   "through the same header and CMake target")
    license = "MIT"
    homepage = "https://github.com/tronkko/dirent"
    url = ""  # CI fills this
    topics = ("dirent", "directory", "portable", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Run the upstream unit tests (9 CTest entries) during the build.
        tc.cache_variables["DIRENT_TESTS"] = "ON"
        # Examples are CLI demo programs, not part of the deliverable, and
        # are not installed by upstream; keep them out of the build so the
        # package stays a pure header library (R38: no bin/ artifacts).
        tc.cache_variables["DIRENT_EXAMPLES"] = "OFF"
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream tests: t-compile, t-dirent, t-scandir, t-unicode,
        # t-cplusplus, t-telldir, t-strverscmp, t-utf8, t-symlink.
        #
        # On HarmonyOS PC the /tmp mount is read-only (erofs); upstream tests
        # hardcode /tmp/ unless $TMPDIR is honored (see patches 0001/0003).
        # Provide a dedicated writable temp dir inside the build folder so
        # t-symlink/t-scandir can run for real.
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        os.environ["TMPDIR"] = test_tmp
        os.environ["TMP"] = test_tmp
        os.environ["TEMP"] = test_tmp
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Ship the MIT license alongside the installed header.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id

    def package_info(self):
        # Mirror the upstream CMake package name/target so consumers can use
        # find_package(Dirent) + link the `dirent` target.
        self.cpp_info.set_property("cmake_file_name", "Dirent")
        self.cpp_info.set_property("cmake_target_name", "dirent")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # The bundled include/dirent.h is a Windows/MSVC compatibility shim
        # (it pulls in <windows.h>) — exactly as upstream DirentConfig.cmake
        # mirrors CMAKE_C_COMPILER_ID==MSVC, only MSVC builds get the include
        # path; on Linux/OHOS consumers use the system dirent.h through the
        # `dirent` CMake target (which stays an empty INTERFACE target),
        # matching what upstream itself does on non-MSVC compilers.
        if self.settings.compiler == "msvc":
            self.cpp_info.includedirs = ["include/dirent-1.26"]
        else:
            self.cpp_info.includedirs = []
