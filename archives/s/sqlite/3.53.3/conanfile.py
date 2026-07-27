#!/usr/bin/env python3
"""Conan recipe — sqlite 3.53.3 (manual build, autosetup incompatible with HMDFS).

sqlite uses autosetup (not autotools). The jimsh0 bootstrap TCL interpreter
cannot exec subprocesses on HarmonyOS HMDFS, so configure fails.
This recipe uses manual clang compilation instead (equivalent to Makefile.fallback).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SqliteConan(ConanFile):
    name = "sqlite"
    version = "3.53.3"
    description = "Self-contained, serverless, zero-configuration SQL database engine"
    license = "Public-Domain"
    homepage = "https://www.sqlite.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        defines = (
            "-DSQLITE_ENABLE_RTREE "
            "-DSQLITE_ENABLE_FTS5 "
            "-DSQLITE_ENABLE_COLUMN_METADATA "
            "-DSQLITE_ENABLE_UNLOCK_NOTIFY "
            "-DSQLITE_SECURE_DELETE "
            "-DSQLITE_ENABLE_DBSTAT_VTAB"
        )
        cflags = " ".join(self._get_cflags())
        self.run(f"clang -c sqlite3.c -o sqlite3.o {defines} {cflags}")
        self.run(f"clang -o sqlite3 shell.c sqlite3.o {cflags}")
        self.run("llvm-ar rcs libsqlite3.a sqlite3.o")

    def _get_cflags(self):
        flags = ["-fPIC", "-O2"]
        if self.settings.build_type == "Debug":
            flags = ["-fPIC", "-g"]
        return flags

    def package(self):
        copy(self, "sqlite3", src=".", dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libsqlite3.a", src=".", dst=os.path.join(self.package_folder, "lib"))
        copy(self, "sqlite3.h", src=".", dst=os.path.join(self.package_folder, "include"))
        copy(self, "sqlite3ext.h", src=".", dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["sqlite3"]
        self.cpp_info.includedirs = ["include"]
