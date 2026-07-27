#!/usr/bin/env python3
"""Conan recipe for libmpack — MessagePack serialization library in C.

libmpack uses a plain Makefile with GNU libtool. Since libtool is not
available on HarmonyOS, this recipe builds via the amalgamation approach:
concatenate all headers/sources into a single translation unit, compile,
and archive into a static library.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmpackConan(ConanFile):
    name = "libmpack"
    version = "1.0.5"
    description = "Small binary serialization/RPC library implementing msgpack and msgpack-rpc"
    license = "MIT"
    homepage = "https://github.com/libmpack/libmpack"
    url = "https://github.com/libmpack/libmpack"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Use Conan toolchain to set up compiler/flags from profile
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        build_dir = os.path.join(self.build_folder, "build")
        os.makedirs(build_dir, exist_ok=True)

        # Generate amalgamation header: concat all .h files, remove #include "..."
        hdrs = ["core.h", "conv.h", "object.h", "rpc.h"]
        amalg_h = os.path.join(build_dir, "mpack.h")
        with open(amalg_h, "w") as out:
            for h in hdrs:
                with open(os.path.join(src, h)) as f:
                    for line in f:
                        if not line.startswith('#include "'):
                            out.write(line)

        # Generate amalgamation source: header + all .c files, remove #include "..."
        srcs = ["core.c", "conv.c", "object.c", "rpc.c"]
        amalg_c = os.path.join(build_dir, "mpack.c")
        with open(amalg_c, "w") as out:
            with open(amalg_h) as f:
                for line in f:
                    if not line.startswith('#include "'):
                        out.write(line)
            for s in srcs:
                with open(os.path.join(src, s)) as f:
                    for line in f:
                        if not line.startswith('#include "'):
                            out.write(line)

        # Compile — CC/CFLAGS/AR come from Conan-generated conanbuild.sh
        build_type = self.settings.build_type
        if build_type == "Release":
            xcflags = "-O3 -DNDEBUG"
        elif build_type == "Debug":
            xcflags = "-O0 -g -DDEBUG"
        else:
            xcflags = "-O2"

        obj_path = os.path.join(build_dir, "mpack.o")
        self.run(f'$CC -std=c99 -Wall -Wextra -Wconversion -pedantic $CFLAGS {xcflags} '
                 f'-c "{amalg_c}" -o "{obj_path}"')

        # Create static library
        lib_path = os.path.join(build_dir, "libmpack.a")
        self.run(f'$AR rcs "{lib_path}" "{obj_path}"')

    def package(self):
        build_dir = os.path.join(self.build_folder, "build")
        # Install static library
        copy(self, "libmpack.a", dst=os.path.join(self.package_folder, "lib"), src=build_dir)
        # Install amalgamation header
        copy(self, "mpack.h", dst=os.path.join(self.package_folder, "include"), src=build_dir)
        # Install license
        copy(self, "LICENSE-MIT", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["mpack"]
