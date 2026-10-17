#!/usr/bin/env python3
"""Conan recipe — sqlite_orm 1.9.1 (CMake, header-only).

sqlite_orm is a light header-only ORM wrapper around SQLite3's C API.
Upstream builds an INTERFACE target (include/sqlite_orm/sqlite_orm.h) that
links SQLite::SQLite3; on OHOS the public API only needs the sqlite3 C
library at link time, which we model as a regular Conan dependency.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SqliteOrmConan(ConanFile):
    name = "sqlite_orm"
    version = "1.9.1"
    description = "Light header-only ORM wrapper for SQLite3 C API."
    license = "AGPL-3.0"
    homepage = "https://github.com/fnc12/sqlite_orm"
    url = "https://github.com/fnc12/sqlite_orm"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # sqlite_orm.h is a single header that only needs the sqlite3 C API;
        # no CMAKE_SYSTEM_NAME override required (header-only INTERFACE target).
        tc.generate()

    def build(self):
        # header-only: nothing to compile; patches still applied for parity
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []  # header-only
        self.cpp_info.requires = ["sqlite3::sqlite3"]
