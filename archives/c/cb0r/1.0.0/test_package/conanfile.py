#!/usr/bin/env python3
"""Conan consumer test for cb0r 1.0.0 — CBOR decoder/encoder library."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class Cb0rTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )

        cb0r_info = self.dependencies[self.tested_reference_str].cpp_info
        include_dirs = cb0r_info.includedirs
        lib_dirs = cb0r_info.libdirs
        libs = cb0r_info.libs

        include_flags = " ".join(f'-I"{d}"' for d in include_dirs)
        lib_flags = " ".join(f'-L"{d}"' for d in lib_dirs)
        link_flags = " ".join(f"-l{l}" for l in libs)

        source = Path(self.source_folder, "test.c")
        output = Path(
            self.build_folder,
            "test_cb0r.exe" if str(self.settings.os) == "Windows" else "test_cb0r",
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        self.run(
            f'"{cc}" -std=c99 {include_flags} "{source}" '
            f'{lib_flags} {link_flags} -o "{output}"'
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile-only consumer test")
            return
        exe = Path(
            self.build_folder,
            "test_cb0r.exe" if str(self.settings.os) == "Windows" else "test_cb0r",
        )
        self.run(f'"{exe}"', env="conanrun")
