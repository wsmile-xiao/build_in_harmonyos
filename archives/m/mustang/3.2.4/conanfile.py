#!/usr/bin/env python3
"""Conan recipe — mustang 3.2.4 (bare Makefile).

MUSTANG (MUltiple STuructural AligNment alGorithm) aligns protein structures.
Build system: plain Makefile (no configure step), zero external dependencies.
Upstream hardcodes CPP=g++ and CPPFLAGS="-traditional -Wall -O3"; this recipe
overrides both on the make command line to use the OHOS clang toolchain
(clang rejects "-traditional").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MustangConan(ConanFile):
    name = "mustang"
    version = "3.2.4"
    description = "MUSTANG: MUltiple STuructural AligNment alGorithm for proteins"
    license = "BSD-3-Clause"
    homepage = "http://lcb.infotech.monash.edu.au/mustang"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mustang supports Linux/OHOS only, got {}".format(self.settings.os))

    def build(self):
        apply_conandata_patches(self)  # no-op: conandata.yml declares no patches
        # R33: compiler comes from profile conf, never from shell env vars.
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cxx = comp.get("cpp", "clang++") if comp else "clang++"
        # Upstream Makefile hardcodes g++ and "-traditional" (GCC cpp only);
        # override both via make command-line variables (no patch needed).
        self.run(
            "make -j1 CPP='{}' CPPFLAGS='-Wall -O3'".format(cxx),
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        # Upstream installs nothing; ship the versioned binary as "mustang".
        copy(self, "bin/mustang-3.2.4", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        os.rename(os.path.join(self.package_folder, "bin", "mustang-3.2.4"),
                  os.path.join(self.package_folder, "bin", "mustang"))
        copy(self, "man/mustang.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
