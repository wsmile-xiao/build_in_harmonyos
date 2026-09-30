#!/usr/bin/env python3
"""Conan recipe — medianfilter 1.0.0.

Heap-free, O(n/2)-worst-case sliding-window median filter for embedded
systems (accabog/MedianFilter).  C API (MedianFilter.h/.c) + C++ header-only
template (MedianFilter.hpp).  No dependencies beyond <stdint.h>/<cstdint>;
window size and median pointer are tracked incrementally with zero malloc.

Build system: plain Makefile (upstream only builds tests/examples).
This recipe builds the C part into a static library, compiles and runs the
three upstream test executables (stress_test / circular_test / test_cpp),
and installs headers + lib.  License: MIT.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MedianfilterConan(ConanFile):
    name = "medianfilter"
    version = "1.0.0"
    description = "Heap-free sliding-window median filter for embedded C/C++ (O(n/2) worst-case insert)"
    license = "MIT"
    homepage = "https://github.com/accabog/MedianFilter"
    url = "https://github.com/accabog/MedianFilter"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: resolve compilers from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        ar = shutil.which("llvm-ar") or "ar"
        cflags = "-O2 -std=c11 -Wall -Wextra -Werror -fPIC"
        cxxflags = "-O2 -std=c++17 -Wall -Wextra -Werror -fPIC"
        src = self.source_folder

        # 1. Static library from the C API
        self.run(f"{cc} {cflags} -I{src} -c {src}/MedianFilter.c -o {src}/MedianFilter.o", cwd=src)
        self.run(f"{ar} rcs {src}/libmedianfilter.a {src}/MedianFilter.o", cwd=src)

        # 2. Build and RUN all upstream test executables (hard gate)
        self.run(f"{cc} {cflags} -I{src} {src}/tests/stress_test.c {src}/MedianFilter.c -o {src}/stress_test", cwd=src)
        self.run(f"{cc} {cflags} -I{src} {src}/tests/circular_test.c {src}/MedianFilter.c -o {src}/circular_test", cwd=src)
        self.run(f"{cxx} {cxxflags} -I{src} {src}/tests/test_cpp.cpp -o {src}/test_cpp", cwd=src)
        self.run("./stress_test", cwd=src)
        self.run("./circular_test", cwd=src)
        self.run("./test_cpp", cwd=src)

    def package(self):
        copy(self, "libmedianfilter.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "MedianFilter.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "MedianFilter.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["medianfilter"]
        self.cpp_info.set_property("cmake_file_name", "medianfilter")
        self.cpp_info.set_property("cmake_target_name", "medianfilter::medianfilter")