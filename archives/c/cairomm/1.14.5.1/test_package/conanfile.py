"""Conan test_package — cairomm 1.14.5.

Verifies the cairomm-1.0 C++ API can be compiled and linked.
HarmonyOS musl dynamic linker hard-codes its search path and restricts
dlopen/run-time of libraries outside that path, so we validate the
produced ELF's NEEDED entries statically (llvm-readelf) instead of
executing the binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CairommTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # HarmonyOS: static validation only.  Inspect the built ELF's
        # NEEDED entries to confirm it links libcairomm-1.0.so.1.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_cairomm")
        readelf = "/data/service/hnp/bin/llvm-readelf"
        out_file = os.path.join(self.cpp.build.bindirs[0], "readelf_out.txt")
        self.run(f'{readelf} --dynamic {bin_path} > {out_file}', env="conanbuild")
        with open(out_file, encoding="utf-8") as f:
            out = f.read()
        if "libcairomm-1.0.so.1" not in out:
            raise Exception(
                f"NEEDED libcairomm-1.0.so.1 not found in {bin_path}; output:\n{out}"
            )
        self.output.info("cairomm 1.14.5: NEEDED libcairomm-1.0.so.1 confirmed")
