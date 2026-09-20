#!/usr/bin/env python3
"""Conan recipe — notcurses 3.0.17 (CMake).

TUI library for modern terminal applications with multimedia support.
Depends on ncurses/6.4, libunistring/1.0, libdeflate/1.25 (all from Conan registry).

R32: settings.os must check in ("Linux", "OHOS").
R33: Compilers from Conan toolchain, not shell env vars.

Platform differences are handled via configure-time feature detection and
build options (no platform macros in patches, R8):
  0001-CMakeLists.txt.patch  - check_symbol_exists() probes for
       HAVE_PTHREAD_CANCEL/HAVE_PPOLL/HAVE_MREMAP + optional libm/librt +
       NOTCURSES_TERM_QUIRKS option
  0002-src-demo-input.c.patch - cooperative stop_input() when no pthread_cancel
  0003-src-demo-reel.c.patch  - cooperative kill_tablet() when no pthread_cancel
  0004-src-lib-fbuf.h.patch   - malloc/realloc/free fallback when no mremap
  0005-src-lib-fd.c.patch     - stop-pipe wake for fdplane destroy, no cancel
  0006-src-lib-in.c.patch     - poll() fallback when no ppoll; cooperative
       input-thread shutdown with join + free (no detach/leak)
  0007-src-lib-in.h.patch     - inputlayer_clear_initdata declaration
  0008-src-lib-internal.h.patch - cancel_and_join degrades to join-only
  0009-src-lib-reader.c.patch - Enter-as-newline + cursor fix (term quirks)
  0010-src-lib-termdesc.c.patch - skip unanswered status queries (term quirks)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class NotcursesConan(ConanFile):
    name = "notcurses"
    version = "3.0.17"
    description = "TUI library for modern terminal applications with multimedia support"
    license = "Apache-2.0"
    homepage = "https://github.com/dankamongmen/notcurses"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")
        self.requires("libunistring/1.0")
        self.requires("libdeflate/1.25")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "notcurses is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Shared build: runtime .so resolution via Conan-managed dependency chain
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build options
        tc.variables["USE_MULTIMEDIA"] = "none"
        tc.variables["USE_STATIC"] = "OFF"
        tc.variables["USE_CXX"] = "ON"
        tc.variables["USE_DOCTEST"] = "OFF"
        tc.variables["USE_PANDOC"] = "OFF"
        tc.variables["USE_POC"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_FFI_LIBRARY"] = "OFF"
        tc.variables["USE_GPM"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Terminal workarounds (skip status queries the terminal never
        # answers; treat synthesized Enter as newline). Enabled for OHOS,
        # where the stock terminal exhibits both behaviors.
        tc.variables["NOTCURSES_TERM_QUIRKS"] = "ON" if self.settings.os == "OHOS" else "OFF"

        # The CMakeLists.txt uses check_include_file() and find_library()
        # instead of find_package(), so CMakeDeps alone doesn't provide
        # the include/lib paths to those checks. Collect them here.
        cflags_extra = []
        lib_dirs = []
        for dep_name in ["ncurses", "libunistring", "libdeflate"]:
            dep = self.dependencies[dep_name]
            pkg = dep.package_folder
            if pkg:
                inc = os.path.join(pkg, "include")
                lib = os.path.join(pkg, "lib")
                if os.path.isdir(inc):
                    cflags_extra.append("-I" + inc)
                if os.path.isdir(lib):
                    lib_dirs.append(lib)
        if cflags_extra:
            tc.extra_cflags.extend(cflags_extra)
        if lib_dirs:
            tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
            ld_flags = " ".join("-L" + d for d in lib_dirs)
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = ld_flags + " ${CMAKE_EXE_LINKER_FLAGS}"
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = ld_flags + " ${CMAKE_SHARED_LINKER_FLAGS}"

        tc.generate()

        # Generate CMake config and pkg-config files for dependencies
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # notcurses++ (C++ bindings) first: it depends on notcurses
        self.cpp_info.libs = ["notcurses++", "notcurses", "notcurses-core"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "notcurses")
        self.cpp_info.set_property("cmake_target_name", "notcurses::notcurses")
        self.cpp_info.set_property("pkg_config_name", "notcurses")
