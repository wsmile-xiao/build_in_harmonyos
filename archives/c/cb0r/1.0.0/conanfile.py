#!/usr/bin/env python3
"""Conan recipe for cb0r 1.0.0 — Minimal Zero-Footprint CBOR Decoder in C.

cb0r has no build system (bare Makefile with hardcoded gcc).  The recipe
compiles src/cb0r.c directly and runs the upstream test/test.c on
Linux / OHOS.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get


class Cb0rConan(ConanFile):
    name = "cb0r"
    version = "1.0.0"
    description = "Minimal Zero-Footprint CBOR Decoder in C"
    license = "Unlicense"
    homepage = "https://github.com/quartzjer/cb0r"
    url = "https://github.com/quartzjer/cb0r"
    topics = ("cbor", "encoder", "decoder", "binary", "serialization", "c")
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="cb0r-1.0.0.tar.gz",
            strip_root=True,
        )

    def _compiler_executables(self):
        """Return the tools.build:compiler_executables conf dict."""
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.info("Skipping upstream tests on non-Linux/OHOS host")
            return

        compilers = self._compiler_executables()
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        ar = compilers.get("ar", "llvm-ar")

        src = self.source_folder

        # Compile library object
        self.run(
            f'"{cc}" -std=gnu99 -Wall -c -I"{src}/src" '
            f'"{src}/src/cb0r.c" -o "{self.build_folder}/cb0r.o"'
        )

        # Create static archive
        self.run(
            f'"{ar}" rcs "{self.build_folder}/libcb0r.a" '
            f'"{self.build_folder}/cb0r.o"'
        )

        # Compile and run upstream tests
        self.run(
            f'"{cc}" -std=gnu99 -Wall -I"{src}/src" '
            f'"{src}/test/test.c" "{src}/src/cb0r.c" '
            f'-o "{self.build_folder}/cb0r_test"'
        )
        self.run(f'"{self.build_folder}/cb0r_test"')

    def package(self):
        copy(
            self,
            "cb0r.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libcb0r.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "UNLICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["cb0r"]
        self.cpp_info.set_property("cmake_file_name", "cb0r")
        self.cpp_info.set_property("cmake_target_name", "cb0r::cb0r")
        self.cpp_info.set_property("pkg_config_name", "cb0r")
