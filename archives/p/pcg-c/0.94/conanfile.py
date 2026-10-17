#!/usr/bin/env python3
"""Conan recipe for pcg-c — Makefile-based C library.

PCG is a family of simple fast space-efficient statistically good
algorithms for random number generation.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class PcgcConan(ConanFile):
    name = "pcg-c"
    version = "0.94"
    description = "PCG Random Number Generation, C Edition"
    license = "Apache-2.0 OR MIT"
    homepage = "https://www.pcg-random.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Build only the library, not tests
        # Note: source is in self.source_folder, which contains the 'src' subdirectory
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f"make -C {src_dir} -j1")

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.a", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["pcg_random"]
