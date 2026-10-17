#!/usr/bin/env python3
"""Conan recipe for hsdlib 0.4.1.

hsdlib is a C library (habedi/hsdlib) providing hardware-accelerated distance
metrics and similarity measures for high-dimensional data, with runtime SIMD
dispatch (AVX/AVX2/AVX512 on AMD64, NEON/SVE on AArch64).

Upstream ships a plain Makefile (no configure script) that builds
lib/libhsd.a + lib/libhsd.so from src/ and a C test suite in tests/.
There is no `install` target, so this recipe runs `make build` and copies
the artifacts (lib/*.a, lib/*.so, include/hsdlib.h) into the package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HsdlibConan(ConanFile):
    name = "hsdlib"
    version = "0.4.1"
    description = "Hardware-accelerated distance metrics and similarity measures for high-dimensional data"
    license = "MIT"
    homepage = "https://github.com/habedi/hsdlib"
    url = "https://github.com/habedi/hsdlib"

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

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (dict form), never bare ${CC}/${CFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        build_type = "release" if self.settings.build_type == "Release" else "debug"
        # R9: -j1; Makefile SHELL patched to fall back to /bin/sh (OHOS has no /bin/bash).
        # Makefile lives in source_folder (basic_layout keeps build in its own dir).
        self.run(f"make -C {self.source_folder} build CC={cc} AR={ar} "
                 f"RANLIB={ranlib} BUILD_TYPE={build_type} -j1")

    def package(self):
        # conan copy() preserves the matched file's relative dir structure under dst,
        # so point src at the subdir and use a flat pattern to avoid include/include nesting.
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.a", os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "*.so*", os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # library file is libhsd.a / libhsd.so -> link name "hsd"
        self.cpp_info.libs = ["hsd"]
