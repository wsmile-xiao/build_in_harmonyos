#!/usr/bin/env python3
"""Conan recipe — genann 1.1.1

Genann: minimal C artificial neural network library (zlib License).
Single-source C99 library (genann.c + genann.h), no external dependencies
beyond libm. Upstream Makefile builds the test binary and 4 examples but
has no install target for the library itself, so this recipe compiles
genann.c into libgenann.a and installs header + static lib.

Build: plain Makefile (no configure). CFLAGS from upstream contain
`-march=native` which is invalid for cross-compilation, so the recipe
passes its own CFLAGS (via GnuToolchain) like other plain-Makefile
formulas (aa3d precedent, R9: -j1 due to HMDFS jobserver issues).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class GenannConan(ConanFile):
    name = "genann"
    version = "1.1.1"
    description = "Genann - minimal C artificial neural network library (feedforward ANN, backprop training)"
    license = "Zlib"
    homepage = "https://github.com/codeplea/genann"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # Upstream ships only a static lib artifact (libgenann.a). OHOS
    # adaptation keeps static (R26 default for system-adjacent libs).
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"genann/{self.version} is only supported on Linux/OHOS, "
                f"not {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        # Override upstream `-march=native` (invalid for cross-compile) and
        # `-O3 -g` with the Conan toolchain CFLAGS. R33: compilers come from
        # Conan conf, never bare shell env vars.
        tc.extra_cflags = []
        tc.extra_cxxflags = []
        tc.generate()

    def build(self):
        # 本配方无补丁（conandata.yml patches 为空），调用保持门禁 G1 通过
        apply_conandata_patches(self)
        # R33: get compiler from conan conf
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: -j1 for simple makefiles (HMDFS jobserver issues on OHOS)
        self.run(f'make -j1 test CC="{cc}" '
                 f'CFLAGS="-Wall -Wshadow -O2 -fPIC"', cwd=self.source_folder)

    def package(self):
        # Install public header and static lib (this recipe does not use the
        # upstream Makefile install target — there is none for the library).
        copy(self, "genann.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # genann.o was built by make test; archive it into libgenann.a
        self.run("ar rcs libgenann.a genann.o", cwd=self.source_folder)
        copy(self, "libgenann.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # Keep license for packaged metadata
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["genann"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]