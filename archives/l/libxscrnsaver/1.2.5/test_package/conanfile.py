#!/usr/bin/env python3
"""Consumer smoke test for libxscrnsaver."""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class LibXScrnSaverTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build(self):
        self._ensure_writable_tmpdir()
        compiler = self._c_compiler()
        source = Path(self.source_folder, "test.c")
        output = Path(self.build_folder, "test_xscrnsaver")
        output.parent.mkdir(parents=True, exist_ok=True)

        include_dirs, lib_dirs, libs, system_libs = self._dependency_flags()
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        lib_dir_flags = " ".join(f'-L"{path}"' for path in lib_dirs)
        link_flags = " ".join(f"-l{name}" for name in libs + system_libs)
        self.run(
            f'"{compiler}" -std=c11 -Wall -Wextra -Werror '
            f'{include_flags} "{source}" -o "{output}" '
            f"{lib_dir_flags} {link_flags}",
            env="conanbuild",
        )

    def test(self):
        executable = Path(self.build_folder, "test_xscrnsaver")
        if not executable.is_file() or executable.stat().st_size == 0:
            raise ConanException("consumer executable was not built")
        if cross_building(self):
            self.output.info("cross-building: compile/link smoke completed")
            return
        self.run(f'"{executable}"', env="conanrun")

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c")
        if compiler and Path(compiler).is_file():
            return compiler
        compiler = shutil.which("clang") or shutil.which("cc")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define an existing C compiler"
            )
        return compiler

    def _ensure_writable_tmpdir(self):
        tmpdir = Path(self.build_folder, "tmp")
        tmpdir.mkdir(parents=True, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            os.environ[name] = str(tmpdir)

    def _dependency_flags(self):
        tested = self.dependencies[self.tested_reference_str]
        ordered = [tested]
        for _, dependency in self.dependencies.items():
            if dependency is not tested:
                ordered.append(dependency)

        include_dirs = []
        lib_dirs = []
        libs = []
        system_libs = []
        for dependency in ordered:
            cpp_info = dependency.cpp_info.aggregated_components()
            include_dirs.extend(cpp_info.includedirs)
            lib_dirs.extend(cpp_info.libdirs)
            libs.extend(cpp_info.libs)
            system_libs.extend(cpp_info.system_libs)

        return (
            self._dedupe(include_dirs),
            self._dedupe(lib_dirs),
            self._dedupe(libs),
            self._dedupe(system_libs),
        )

    def _dedupe(self, values):
        result = []
        seen = set()
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result
