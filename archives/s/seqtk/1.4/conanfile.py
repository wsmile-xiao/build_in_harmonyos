#!/usr/bin/env python3
"""Conan recipe for seqtk 1.4."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SeqtkConan(ConanFile):
    name = "seqtk"
    version = "1.4"
    description = "Fast and lightweight FASTA/FASTQ processing toolkit"
    license = "MIT"
    homepage = "https://github.com/lh3/seqtk"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"seqtk supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _ohos_tool(self, name, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if name in compilers:
            return compilers[name]
        return default

    def _dependency_paths(self, dependency, field):
        paths = []
        for path in getattr(dependency.cpp_info, field, []):
            paths.append(
                path
                if os.path.isabs(path)
                else os.path.join(dependency.package_folder, path)
            )
        return paths

    def build(self):
        apply_conandata_patches(self)
        zlib = self.dependencies["zlib"]
        include_flags = [
            f"-I{path}" for path in self._dependency_paths(zlib, "includedirs")
        ]
        library_flags = [
            f"-L{path}" for path in self._dependency_paths(zlib, "libdirs")
        ]
        optimization_flags = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        cflags = (
            f"{optimization_flags} -Wall -Wextra -Wno-unused-function "
            + " ".join(include_flags)
        )
        compiler = self._compiler()
        if library_flags:
            compiler = f"{compiler} {' '.join(library_flags)}"
        self.run(
            f'make -j1 CC="{compiler}" CFLAGS="{cflags}"',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "seqtk", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir, keep_path=False)

        binary = os.path.join(bin_dir, "seqtk")
        if str(self.settings.os) == "OHOS":
            sign_tool = self._ohos_tool(
                "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
            )
            objcopy = self._ohos_tool(
                "objcopy", "/data/service/hnp/bin/llvm-objcopy"
            )
            self.run(
                f'"{objcopy}" --remove-section .codesign "{binary}" '
                "2>/dev/null || true",
                cwd=self.package_folder,
            )
            if sign_tool:
                signed = binary + ".signed"
                self.run(
                    f'"{sign_tool}" sign -inFile "{binary}" '
                    f'-outFile "{signed}" -selfSign 1',
                    cwd=self.package_folder,
                    quiet=True,
                )
                os.replace(signed, binary)
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
