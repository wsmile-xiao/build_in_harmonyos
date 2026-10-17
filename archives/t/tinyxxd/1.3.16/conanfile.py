#!/usr/bin/env python3
"""Conan recipe for tinyxxd 1.3.16 — a small self-contained xxd clone.

tinyxxd is a single C11 translation unit (main.c) that dumps binary files to
hex / binary / little-endian / C-include formats and can convert them back
(-r). It has no dependencies beyond the C standard library.

The upstream Makefile adds -Werror plus ASan in `make test`, and `make test`
downloads vim's xxd to diff against; neither is suitable for a clean CI
worker, so the binary is built directly and the self-contained upstream test
cases are reproduced by test_package/test_tinyxxd.py.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TinyxxdConan(ConanFile):
    name = "tinyxxd"
    version = "1.3.16"
    description = "A tiny self-contained xxd clone: hex/binary dump and reverse"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/xyproto/tinyxxd"
    url = "https://github.com/xyproto/tinyxxd"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        self._cc = str(executables.get("c") or "clang")

    def build(self):
        apply_conandata_patches(self)
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"
        self.run(
            f'{self._cc} -std=c11 -D_GNU_SOURCE -fstack-protector-strong {opt} '
            f'-o "{self.build_folder}/tinyxxd" "{self.source_folder}/main.c"'
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "tinyxxd", src=self.build_folder, dst=bin_dir, keep_path=False)
        os.chmod(os.path.join(bin_dir, "tinyxxd"), 0o755)
        copy(self, "tinyxxd.1", src=self.source_folder, dst=man_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
