#!/usr/bin/env python3
"""Conan recipe for sqlite3 3.53.4.

The official autoconf bundle uses autosetup and a bootstrap Tcl interpreter.
That generator cannot execute child processes on the OHOS HMDFS worker, so the
amalgamation is compiled directly with the same feature set on every target.
The package is static-only to avoid colliding with any platform sqlite3.
"""

import os
import shlex

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Sqlite3Conan(ConanFile):
    name = "sqlite3"
    version = "3.53.4"
    package_type = "library"
    description = "Self-contained, serverless, zero-configuration SQL database engine"
    license = "Public-Domain"
    homepage = "https://www.sqlite.org/"
    url = ""  # CI fills this repository URL

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def requirements(self):
        # SQLite has no Conan dependencies; pthread and dl are platform libs.
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # The amalgamation build writes objects in the source directory.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, fallback):
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        value = tools.get(key) if tools else None
        return value or fallback

    @staticmethod
    def _quote(value):
        if os.name == "nt" and any(ch.isspace() for ch in value):
            return '"{}"'.format(value.replace('"', '\\"'))
        return shlex.quote(value)

    def _llvm_tool(self, name, fallback):
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        configured = tools.get(name) if tools else None
        if configured:
            return configured
        compiler = self._tool("c", "clang")
        sibling = os.path.join(os.path.dirname(compiler), "llvm-{}".format(name))
        if os.path.isfile(sibling):
            return sibling
        return fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._tool("c", "clang")
        ar = self._llvm_tool("ar", "llvm-ar")
        cflags = [
            "-fPIC",
            "-O2",
            "-I.",
            "-DSQLITE_THREADSAFE=1",
            "-DSQLITE_ENABLE_RTREE",
            "-DSQLITE_ENABLE_FTS5",
            "-DSQLITE_ENABLE_COLUMN_METADATA",
            "-DSQLITE_ENABLE_UNLOCK_NOTIFY",
            "-DSQLITE_SECURE_DELETE",
            "-DSQLITE_ENABLE_DBSTAT_VTAB",
            "-DSQLITE_DEFAULT_MEMSTATUS=0",
        ]
        flags = " ".join(cflags)
        compiler = self._quote(cc)
        archiver = self._quote(ar)
        self.run("{} {} -c sqlite3.c -o sqlite3.o".format(compiler, flags))
        self.run("{} rcs libsqlite3.a sqlite3.o".format(archiver))
        self.run("{} {} -c shell.c -o shell.o".format(compiler, flags))
        system_libs = "" if str(self.settings.os) == "Windows" else "-ldl -lpthread -lm"
        self.run("{} shell.o sqlite3.o -o sqlite3 {}".format(compiler, system_libs))

    def package(self):
        copy(self, "sqlite3.h", src=self.build_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "sqlite3ext.h", src=self.build_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libsqlite3.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "sqlite3", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sqlite3.1", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = ["sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "sqlite3")
        self.cpp_info.set_property("cmake_target_name", "sqlite3::sqlite3")
        self.cpp_info.set_property("pkg_config_name", "sqlite3")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
