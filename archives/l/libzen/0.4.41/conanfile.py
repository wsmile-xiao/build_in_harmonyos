#!/usr/bin/env python3
"""Conan recipe for libzen 0.4.41 (ZenLib) — CMake-based, HarmonyOS PC.

ZenLib is the small C++ utility library of the MediaArea family (same
family as libmediainfo): Ztring (UTF-8/Unicode string handling),
File/Dir/FileName, CriticalSection, Thread, InfoMap, Translation.

It has no third-party dependencies: upstream CMake uses only Threads
(-lpthread) and optional PkgConfig for .pc generation, so requirements()
is empty by design.

OHOS adaptation notes (root causes):
  - Build scripts live in Project/CMake (the tarball root has no
    CMakeLists.txt), so configure with build_script_folder="Project/CMake".
    With get(strip_root=True) the whole tree shifts up one level and the
    CMakeLists' relative path ../../Source still resolves to
    <source>/Source, so no CMakeLists patch is needed.
  - ZenLib declares cmake_minimum_required(3.1.0); CMake >= 4 dropped
    < 3.5 compatibility, so CMAKE_POLICY_VERSION_MINIMUM=3.5 is passed
    (same approach as libmediainfo/25.07; keeps upstream sources intact).
  - Thread::ForceTerminate() calls pthread_cancel, which does not exist
    in OHOS musl libpthread (verified: nm -D shows no symbol, and a
    cross link probe fails with "undefined symbol: pthread_cancel").
    Patch 0001 declares pthread_cancel as a weak symbol (libc probe,
    per project rule R8) and null-checks it before the call: libcs that
    provide the symbol bind to the real function and keep the upstream
    cancellation semantics, while libcs without it (e.g. OHOS musl)
    resolve the reference to NULL and skip the call (cooperative
    termination stays available via RequestTerminate()). No platform
    conditional-compilation macro is introduced.
  - The SSE2 path (ZENLIB_MEMUTILS_SSE2) is never defined anywhere in
    upstream sources, so <emmintrin.h> is never included: no risk on
    arm64.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class LibzenConan(ConanFile):
    name = "libzen"
    version = "0.4.41"
    description = "ZenLib - small C++ utility library from the MediaArea family"
    license = "Zlib"
    homepage = "https://mediaarea.net/en/ZenLib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    topics = ("string", "unicode", "file", "media", "metadata")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        # GitHub tag tarball root is "ZenLib-0.4.41/"; strip_root keeps
        # the Project/ + Source/ relative layout required by the CMake.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        # Upstream defaults (Unicode + large files) are kept explicit for
        # deterministic builds across hosts.
        toolchain.variables["ENABLE_UNICODE"] = True
        toolchain.variables["LARGE_FILES"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake >= 4 dropped compatibility with cmake_minimum_required < 3.5
        # (upstream declares 3.1.0). Measured: the variable must be passed on
        # the cmake command line (-D); setting it inside the toolchain file
        # (plain or CACHE) does NOT take effect, because
        # cmake_minimum_required() runs before the toolchain is processed.
        cmake.configure(build_script_folder="Project/CMake",
                        variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Conan generates its own CMake config files and .pc from
        # package_info; drop the upstream ones to avoid duplicates
        # (same approach as libmediainfo/25.07).
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ZenLib")
        # Upstream ZenLibConfig.cmake provides the target "zen".
        self.cpp_info.set_property("cmake_target_name", "zen")
        self.cpp_info.set_property("pkg_config_name", "libzen")
        self.cpp_info.libs = ["zen"]
        self.cpp_info.includedirs = ["include"]
        if str(self.settings.os) in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
