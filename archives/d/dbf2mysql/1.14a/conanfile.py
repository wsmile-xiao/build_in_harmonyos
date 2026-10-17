#!/usr/bin/env python3
"""Conan recipe for dbf2mysql 1.14a (raw Makefile application)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Dbf2mysqlConan(ConanFile):
    name = "dbf2mysql"
    version = "1.14a"
    description = "Convert between xBase DBF files and MySQL-compatible databases"
    license = "Public-Domain"
    homepage = "https://dbf2mysql.sourceforge.net/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mariadb-connector-c/3.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang")
        ar = compiler_executables.get("ar", "llvm-ar")
        dependency = self.dependencies["mariadb-connector-c"]
        include_dir = os.path.join(dependency.package_folder, "include", "mariadb")
        library_dir = os.path.join(dependency.package_folder, "lib", "mariadb")

        self.run(
            "make -j1 "
            f'CC="{cc}" AR="{ar}" STRIP= VERSION="{self.version}" '
            'CFLAGS="-O2 -Wall -fPIE" '
            f'MYSQLINC="-I{include_dir}" MYSQLLIB="-L{library_dir}" '
            'EXTRALIBS="-lmariadb -lm"',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "dbf2mysql", self.source_folder, bin_dir)
        copy(self, "mysql2dbf", self.source_folder, bin_dir)
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
