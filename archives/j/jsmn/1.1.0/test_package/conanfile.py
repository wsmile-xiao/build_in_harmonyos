#!/usr/bin/env python3
"""Conan consumer test for jsmn 1.1.0."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class JsmnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compiler = self._c_compiler()
        include_dirs = self.dependencies[self.tested_reference_str].cpp_info.includedirs
        source = Path(self.source_folder, "test.c")
        output = Path(self.build_folder, self._exe_name())
        output.parent.mkdir(parents=True, exist_ok=True)

        if str(self.settings.compiler) == "msvc":
            include_flags = " ".join(f'/I"{path}"' for path in include_dirs)
            self.run(f'"{compiler}" /nologo {include_flags} "{source}" /Fe:"{output}"')
        else:
            include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
            self.run(f'"{compiler}" -std=c99 {include_flags} "{source}" -o "{output}"')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile-only consumer test")
            return
        self.run(f'"{Path(self.build_folder, self._exe_name())}"', env="conanrun")

    def _c_compiler(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if compiler:
            return compiler
        if str(self.settings.os) == "Windows" and str(self.settings.compiler) == "msvc":
            return "cl"
        raise ConanException("tools.build:compiler_executables must define the C compiler")

    def _exe_name(self):
        return "test_jsmn.exe" if str(self.settings.os) == "Windows" else "test_jsmn"
