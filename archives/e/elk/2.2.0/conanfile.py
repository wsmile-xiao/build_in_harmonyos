#!/usr/bin/env python3
"""Conan Makefile recipe for elk 2.2.0, the embedded Elk JavaScript engine."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ElkConan(ConanFile):
    name = "elk"
    version = "2.2.0"
    description = "Small embeddable JavaScript engine for C and C++ applications."
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/cesanta/elk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("javascript", "embedded", "c", "interpreter")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define the C compiler"
            )
        ar = compilers.get("ar")
        if not ar:
            compiler_dir = os.path.dirname(cc)
            ar = os.path.join(compiler_dir, "llvm-ar") if compiler_dir else "llvm-ar"

        self.run(
            f"{shlex.quote(cc)} -O2 -fPIC -I. -c elk.c -o elk.o",
            cwd=self.source_folder,
        )
        self.run(f"{shlex.quote(ar)} rcs libelk.a elk.o", cwd=self.source_folder)
        self.run(
            f"make -C test test CC={shlex.quote(cc)} "
            "CFLAGS='-W -Wall -Werror -Wno-deprecated -I.. -O2'",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "elk.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "libelk.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["elk"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "elk")
        self.cpp_info.set_property("cmake_target_name", "elk::elk")
