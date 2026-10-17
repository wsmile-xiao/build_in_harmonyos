#!/usr/bin/env python3
"""Conan recipe — libmpcdec 0.1 (MusePack SV8 decoding library).

Builds the MusePack (MPC) decoder library from the upstream musepack_src_r475
snapshot — the snapshot the distribution packages call "0.1" (Arch Linux ships
libmpcdec 1:0.1+r475, Debian libmpc 0.1~r495).  Only the decoding library and
its public headers are packaged here:

  lib/libmpcdec.a              (or libmpcdec.so with -o shared=True)
  include/mpc/*.h              (mpcdec.h, reader.h, streaminfo.h, ...)

The SV7 encoder, psychoacoustic model and the mpcenc/mpcdec/... command line
tools that live in the same upstream tarball belong to the separate
musepack/r475 recipe and are deliberately not built or packaged here.

Adaptation patches (see patches/ and notes.md):
  1. top-level CMakeLists.txt: cmake_minimum_required >= 3.5 (CMake 4.x
     removed <3.5 compatibility); append to CMAKE_C_FLAGS instead of
     overwriting so Conan/toolchain flags survive, plus -fcommon for the
     legacy tentative definitions (Res_bit/__Cc/__Dc in mpc_decoder.c and
     requant.c) that -fno-common turns into duplicate-symbol link errors;
     build only the libmpcdec + include subdirectories.
  2. libmpcdec/CMakeLists.txt: normalized OUTPUT_NAME (mpcdec) and the
     install rules the upstream CMake files are missing.
  3. include/CMakeLists.txt: install only *.h so the .svn metadata shipped in
     the upstream include tree is not packaged.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibmpcdecConan(ConanFile):
    name = "libmpcdec"
    version = "0.1"
    description = "MusePack (MPC) SV8 audio decoding library (musepack r475 snapshot)"
    license = "BSD-3-Clause"
    homepage = "https://www.musepack.net/"
    url = "https://www.musepack.net/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmpcdec does not support os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # upstream CMake option: SHARED builds libmpcdec.so, else libmpcdec.a
        tc.variables["SHARED"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=os.path.join(self.source_folder, "libmpcdec"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mpcdec"]
