#!/usr/bin/env python3
"""Conan recipe — bwt 2.1.2 (makefile).

bwt: ANSI C implementation of the Burrows-Wheeler transformation (BWT).
Builds libbwt.a (static library) and the sample command-line demo.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class BwtConan(ConanFile):
    name = "bwt"
    version = "2.1.2"
    description = "bwt: An ANSI C implementation of the Burrows-Wheeler transformation (BWT)"
    license = "LGPL-3.0"
    homepage = "https://github.com/MichaelDipperstein/bwt"
    url = "https://github.com/MichaelDipperstein/bwt"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Main bwt source tree
        get(self, **self.conan_data["sources"]["bwt"], strip_root=True)
        # optlist submodule lives in a separate GitHub repo
        get(self, **self.conan_data["sources"]["optlist"], strip_root=True, destination="optlist")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        build = self.build_folder

        # Copy all sources into the build folder for out-of-source layout
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(build, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        # R33: resolve the compiler from the Conan profile conf.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        # Derive the LLVM lib directory from the compiler's real path so that
        # lld (invoked internally by clang during linking) can find its shared
        # libraries (e.g. libxml2.so.16) without hard-coding absolute paths.
        cc_resolved = shutil.which(cc) or cc
        cc_real = os.path.realpath(cc_resolved)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")

        # Build LD_LIBRARY_PATH: prepend llvm_lib if not already present
        existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if llvm_lib not in existing_ld:
            ld_path = f"{llvm_lib}:{existing_ld}" if existing_ld else llvm_lib
        else:
            ld_path = existing_ld

        self.run(
            f"cd {build} && LD_LIBRARY_PATH={ld_path} "
            f"make CC={cc} LD={cc} AR={ar} RANLIB={ranlib} "
            "CFLAGS='-fPIC -O2 -Wall -Wextra -pedantic -ansi -c' LDFLAGS='-O2 -o'",
            env="conanbuild")

    def package(self):
        src = self.source_folder
        build = self.build_folder
        copy(self, "libbwt.a", build, os.path.join(self.package_folder, "lib"))
        copy(self, "bwxform.h", src, os.path.join(self.package_folder, "include"))
        copy(self, "sample", build, os.path.join(self.package_folder, "bin"))
        for lic in ["COPYING", "COPYING.LESSER"]:
            if os.path.exists(os.path.join(src, lic)):
                copy(self, lic, src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["bwt"]
        self.cpp_info.bindirs = ["bin"]