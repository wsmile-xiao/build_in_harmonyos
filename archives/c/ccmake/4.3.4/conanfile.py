#!/usr/bin/env python3
"""Conan recipe — CMake 4.3.4 (command-line build tool incl. ccmake).

Builds the CMake suite (cmake/ctest/cpack/ccmake) for OHOS aarch64 using the
stock CMake build system. The bootstrap self-build is replaced by requiring an
existing host CMake generator (CI provides cmake >= 3.18).

Notes on platform handling (see patches/ and notes.md):
- CMAKE_SYSTEM_NAME is forced to "Linux": CMake 4.3.4 ships Platform/OHOS.cmake
  (include(Platform/Linux)) but no Platform/HarmonyOS.cmake, and the OHOS
  conan toolchain maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, which would
  leave UNIX undefined and make kwsys build its Win32 process implementation.
- ncurses (for ccmake) and openssl (for builtin libcurl https) are consumed
  from the Conan dependency graph as static libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
import os

from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CcmakeConan(ConanFile):
    name = "ccmake"
    version = "4.3.4"
    description = "跨平台构建系统生成器（含 cmake/ctest/cpack/ccmake 命令行工具）"
    license = "BSD-3-Clause"
    homepage = "https://cmake.org/"
    url = "https://cmake.org/download/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Static ncurses for ccmake (R26: keep system /lib clean)
        self.requires("ncurses/6.6")
        # openssl only needed for https via builtin cmcurl
        self.requires("openssl/3.5.6")

    def layout(self):
        # Ninja generator: the make jobserver deadlocks on this platform
        # (toybox sh under nested conan->make), ninja has no such issue.
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        # R32: os checks must accept both Linux and OHOS toolchain variants
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_USE_SYSTEM_LIBRARIES"] = "OFF"
        # Build upstream Tests/ targets so the deterministic unit-test subset
        # (kwsys.* + CMakeLib.*) can run natively in build() — see notes.md.
        tc.variables["BUILD_TESTING"] = "ON"
        # Bundled curl's FindNGHTTP2 module is fragile under the conan
        # toolchain (CURL::nghttp2 target can end up referenced but not
        # created -> generate step fails, seen in CI #44428). HTTP/2 is
        # not needed by any ccmake-suite workflow, so disable it.
        tc.variables["USE_NGHTTP2"] = "OFF"
        tc.variables["BUILD_CursesDialog"] = "ON"  # ccmake
        # Static ncurses for ccmake
        ncurses = self.dependencies["ncurses"]
        nc_lib = _find_static_lib(ncurses.cpp_info.libdirs, "libncursesw.a")
        tc.variables["CURSES_INCLUDE_PATH"] = ncurses.cpp_info.includedirs[0]
        tc.variables["CURSES_CURSES_LIBRARY"] = nc_lib
        tc.variables["CURSES_NCURSES_LIBRARY"] = nc_lib
        tc.variables["CURSES_FORM_LIBRARY"] = nc_lib
        # Static openssl for the bundled curl.
        # NOTE: openssl.cpp_info.includedirs are CONAN-LAYOUT dirs (package
        # root without the "/p" component); the real dirs are the ones the
        # toolchain derives (with "/p"). Use CMAKE_INCLUDE_PATH/LIBRARY_PATH
        # style vars via cpp_info of the dependency graph instead of guessing
        # OPENSSL_ROOT_DIR: pass the exact triple FindOpenSSL needs.
        openssl = self.dependencies["openssl"]
        inc = openssl.cpp_info.includedirs[0]
        # recover the "/p" real layout used on disk (conan2 package dir)
        if os.path.basename(os.path.dirname(inc)) != "p" and os.path.isdir(
                os.path.join(os.path.dirname(inc), "p", "include")):
            inc = os.path.join(os.path.dirname(inc), "p", "include")
        libdir = openssl.cpp_info.libdirs[0]
        if os.path.basename(os.path.dirname(libdir)) != "p" and os.path.isdir(
                os.path.join(os.path.dirname(libdir), "p", "lib")):
            libdir = os.path.join(os.path.dirname(libdir), "p", "lib")
        tc.variables["OPENSSL_INCLUDE_DIR"] = inc
        tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(libdir, "libssl.a")
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(libdir, "libcrypto.a")
        tc.variables["OPENSSL_USE_STATIC_LIBS"] = "TRUE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    # Upstream unit-test subset executed natively with the freshly built
    # ctest: kwsys.* + CMakeLib.* are deterministic and self-contained (no
    # network / host git / host python). Full upstream suite (292 test dirs,
    # 659 registered entries incl. RunCMake feature tests) needs network and
    # host tooling unavailable in the cross sandbox — see notes.md.
    _UPSTREAM_TEST_EXCLUDES = (
        # Sandbox filesystem ignores chmod permission bits, so the
        # SetPermissions/TestFileAccess assertions cannot hold:
        "kwsys.testSystemTools",
        # Sandbox denies unix-socket name binding (bind: Operation not
        # permitted), the debugger adapters abort at startup:
        "CMakeLib.testDebuggerAdapterPipe",
        "CMakeLib.testDebuggerNamedPipe-Project",
        "CMakeLib.testDebuggerNamedPipe-Script",
    )

    def _run_upstream_tests(self):
        if self.conf.get("tools.build:skip_test", check_type=bool):
            return
        ctest = os.path.join(self.build_folder, "bin", "ctest")
        excludes = "|".join(self._UPSTREAM_TEST_EXCLUDES)
        self.output.info(
            "Running upstream ctest subset kwsys.* + CMakeLib.* "
            f"(excluding {len(self._UPSTREAM_TEST_EXCLUDES)} sandbox-limited tests)"
        )
        self.run(
            f'"{ctest}" -R "^(kwsys\\.|CMakeLib\\.)" -E "^({excludes})$" '
            f"--output-on-failure",
            env="conanbuild",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]


def _find_static_lib(libdirs, filename):
    for d in libdirs:
        cand = os.path.join(d, filename)
        if os.path.exists(cand):
            return cand
    return filename
