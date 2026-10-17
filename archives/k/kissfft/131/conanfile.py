#!/usr/bin/env python3
"""Conan recipe — kissfft 131 (Makefile)"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KissfftConan(ConanFile):
    name = "kissfft"
    version = "131"
    description = "A mixed-radix Fast Fourier Transform library - Keep It Simple, Stupid"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mborgerding/kissfft"
    url = "https://cnb.cool/ohpcd/conan-recipes"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "VirtualBuildEnv"

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
        static_flag = "1" if not self.options.shared else "0"
        self.run(f"make CC={os.environ.get('CC', 'clang')} "
                 f"AR={os.environ.get('AR', 'ar')} "
                 f"KISSFFT_TOOLS=0 KISSFFT_STATIC={static_flag} -j1",
                 cwd=self.source_folder)

    def package(self):
        static_flag = "1" if not self.options.shared else "0"
        self.run(f"make install CC={os.environ.get('CC', 'clang')} "
                 f"AR={os.environ.get('AR', 'ar')} "
                 f"PREFIX={self.package_folder} KISSFFT_TOOLS=0 "
                 f"KISSFFT_STATIC={static_flag}",
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["kissfft"]
        self.cpp_info.includedirs = ["include/kissfft"]