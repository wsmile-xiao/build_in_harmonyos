#!/usr/bin/env python3
"""dnswire test_package — Conan L1 official test.

Runs the test binary (linked against the installed dnswire package) and
asserts real API behavior: dnstap protobuf encode/decode round trip.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DnswireTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # dnswire's public headers (dl dnstap.pb-c.h) reference
        # <protobuf-c/protobuf-c.h> and <tinyframe/tinyframe.h>, so the
        # consumer needs both include dirs. The ohpcd protobuf-c/tinyframe
        # binary packages do not populate CMakeDeps INCLUDE_DIRS, so pass
        # the package include dirs explicitly to the test build.
        tc = CMakeToolchain(self)
        try:
            pbc = self.dependencies["protobuf-c"].package_folder
            tc.variables["PROTOBUF_C_INCLUDE_DIR"] = os.path.join(pbc, "include")
        except Exception:
            pass
        try:
            tf = self.dependencies["tinyframe"].package_folder
            tc.variables["TINYFRAME_INCLUDE_DIR"] = os.path.join(tf, "include")
        except Exception:
            pass
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_dnswire")
            if not os.path.exists(bin_path):
                bin_path = os.path.join(self.build_folder, "test_dnswire")
                if not os.path.exists(bin_path):
                    cands = glob.glob(
                        os.path.join(self.build_folder, "**", "test_dnswire"),
                        recursive=True)
                    if cands:
                        bin_path = cands[0]
            # conanrun env provides LD_LIBRARY_PATH for the dependency .so files
            self.run(bin_path, env="conanrun")