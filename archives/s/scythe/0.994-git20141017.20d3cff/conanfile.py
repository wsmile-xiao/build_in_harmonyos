#!/usr/bin/env python3
"""Conan recipe for scythe 0.994-git20141017.20d3cff."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.build import can_run


class ScytheConan(ConanFile):
    name = "scythe"
    version = "0.994-git20141017.20d3cff"
    description = "Bayesian adapter trimmer for 3-prime sequencing contaminants"
    license = "MIT"
    homepage = "https://github.com/vsbuffalo/scythe"
    url = "https://github.com/vsbuffalo/scythe"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        zlib = self.dependencies["zlib"]
        zlib_lib_dir = os.path.join(zlib.package_folder, "lib")
        if not os.path.isdir(zlib_lib_dir):
            zlib_lib_dir = zlib.package_folder
        zlib_static = os.path.join(zlib_lib_dir, "libz.a")
        if not os.path.isfile(zlib_static):
            zlib_static = f"-L{zlib_lib_dir} -lz"

        cflags = "-Wall -pedantic -DVERSION=0.994 -std=gnu99 -O3"
        ldflags = f"{zlib_static} -lm"

        self.run(
            f"make -j1 CC={shlex.quote(cc)} CFLAGS={shlex.quote(cflags)} LDFLAGS={shlex.quote(ldflags)}",
            cwd=self.source_folder,
        )

        test_sources = [
            "src/match.c",
            "src/util.c",
            "src/prob.c",
            "src/tests/tests.c",
        ]
        self.run(
            f"{shlex.quote(cc)} {cflags} {' '.join(test_sources)} -o test {ldflags}",
            cwd=self.source_folder,
        )
        if can_run(self):
            self.run("./test", cwd=self.source_folder)

    def package(self):
        copy(self, "scythe", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
