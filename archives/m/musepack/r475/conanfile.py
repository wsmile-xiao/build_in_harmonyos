#!/usr/bin/env python3
"""Conan recipe — musepack r475 (Musepack/MPC SV8 audio codec).

Pure-C codec family built with the upstream CMakeLists: libmpcdec
(decoder), libmpcenc (SV7 encoder), libmpcpsy (psychoacoustic model)
plus the mpcenc/mpcdec/mpcgain (also mpc2sv8/mpccut/mpcchap/wavcmp)
command line tools.

mpcgain requires libreplaygain and mpcchap requires libcuefile (both
published on ohpcd as r475). The upstream CMake files locate them via
FIND_PATH/FIND_LIBRARY; generate() provisions both dependency packages
into a build_folder-private prefix and seeds the corresponding CMake
cache variables there (R49: never inject a shared /usr/local).

Adaptation patches (see patches/ and notes.md): CMake >= 3.5 minimum,
-fcommon for legacy tentative definitions, x86-only fpu_control.h
guard, POSIX select/time headers, library install rules and normalized
output names, .svn-free header install.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_deps = ("libcuefile/r475", "libreplaygain/r475")


class MusepackConan(ConanFile):
    name = "musepack"
    version = "r475"
    description = "Musepack (MPC) SV8 audio codec: libmpcdec/libmpcenc/libmpcpsy plus mpcenc/mpcdec/mpcgain tools"
    license = ["BSD-3-Clause", "LGPL-2.1-or-later"]
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
                f"musepack does not support os={self.settings.os}")

    def requirements(self):
        for ref in required_deps:
            self.requires(ref)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R49: provision dependency headers/libs into a build_folder-private
        # prefix, then seed the upstream FIND_PATH/FIND_LIBRARY cache vars.
        prefix = os.path.join(self.build_folder, "prefix")
        for dep_name in ("libcuefile", "libreplaygain"):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            pkg = dep.package_folder
            if pkg and os.path.isdir(os.path.join(pkg, "include")):
                copy(self, "*", src=os.path.join(pkg, "include"),
                     dst=os.path.join(prefix, "include"))
            if pkg and os.path.isdir(os.path.join(pkg, "lib")):
                copy(self, "*.a", src=os.path.join(pkg, "lib"),
                     dst=os.path.join(prefix, "lib"))

        tc = CMakeToolchain(self)
        tc.variables["SHARED"] = bool(self.options.shared)
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        if os.path.isdir(inc_dir):
            # FIND_PATH result variables for mpcgain/mpcchap
            tc.variables["REPLAY_GAIN_INCLUDE_DIR"] = inc_dir
            tc.variables["CUEFILE_INCLUDE_DIR"] = inc_dir
        if os.path.isdir(lib_dir):
            # FIND_LIBRARY result variables (static libs shipped by the deps)
            tc.variables["REPLAY_GAIN_LIBRARY"] = os.path.join(lib_dir, "libreplaygain.a")
            tc.variables["CUEFILE_LIBRARY"] = os.path.join(lib_dir, "libcuefile.a")
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
        self.cpp_info.libs = ["mpcdec", "mpcenc", "mpcpsy"]
