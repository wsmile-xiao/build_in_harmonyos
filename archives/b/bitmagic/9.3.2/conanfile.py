#!/usr/bin/env python3
"""Conan recipe — bitmagic 9.3.2 (CMake header-only INTERFACE library).

BitMagic ships as a CMake INTERFACE library — all sources are headers in src/.
We don't need to build the library itself; we just copy headers into the package.
The test_package exercises the API by including bm.h and running a small program.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class BitmagicConan(ConanFile):
    name = "bitmagic"
    version = "9.3.2"
    description = "BitMagic — C++ library for compact bit vectors and integer sets"
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/tlk00/BitMagic"
    url = "https://github.com/tlk00/BitMagic"
    topics = ("bit-vector", "sparse-vector", "header-only", "c++")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_threads": [True, False]}
    default_options = {"with_threads": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # BitMagic itself is header-only; the only optional system dep is pthreads
        # when with_threads=True. Threads come from the system on Linux/OHOS.
        pass

    def validate(self):
        if self.settings.compiler not in ("clang", "gcc"):
            # BitMagic uses GCC/Clang intrinsics in bmsse*/bmavx*; MSVC not tested here.
            self.output.warning(
                f"Compiler {self.settings.compiler} not explicitly supported by BitMagic 9.3.2")

    def layout(self):
        # header-only: no build_folder needed but keep basic_layout for source/package folders
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Header-only: no compile step. Apply patches if any declared in conandata.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []  # header-only
        if self.options.with_threads:
            self.cpp_info.system_libs = ["pthread"]
            self.cpp_info.defines = ["BM_HAVE_THREADS"]