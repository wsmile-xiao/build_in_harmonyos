#!/usr/bin/env python3
"""Conan recipe — sqlite-analyzer 3.53.4.1 (manual)"""
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout

class SqliteAnalyzerConan(ConanFile):
    name = "sqlite-analyzer"
    version = "3.53.4.1"
    description = "SQLite3 Analyzer - disk space utilization analysis tool for SQLite databases"
    license = "Public-Domain"
    homepage = "https://www.sqlite.org/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_folder)

    def requirements(self):
        self.requires("tcl/8.6.16")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        get(self, **self.conan_data["sources"][1], strip_root=True,
            destination=os.path.join(self.source_folder, "amalgamation"))

    def build(self):
        apply_conandata_patches(self)
        amalgamation_dir = os.path.join(self.source_folder, "amalgamation")
        copy(self, "sqlite3.c", src=amalgamation_dir, dst=self.source_folder)
        copy(self, "sqlite3.h", src=amalgamation_dir, dst=self.source_folder)
        tcl_pkg = self.dependencies["tcl"]
        tcl_root = tcl_pkg.package_folder
        tclsh = os.path.join(tcl_root, "bin", "tclsh8.6")
        if not os.path.isfile(tclsh):
            raise ConanException(f"tclsh8.6 not found in tcl package: {tclsh}")
        tcl_include = os.path.join(tcl_root, "include")
        tcl_lib = os.path.join(tcl_root, "lib")
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        cflags = "-fPIC -O2"
        if self.settings.build_type == "Debug":
            cflags = "-fPIC -g"
        self.run(f'{tclsh} tool/mkccode.tcl -DINCLUDE_SQLITE3_C tool/sqlite3_analyzer.c.in > sqlite3_analyzer.c',
                 cwd=self.source_folder, env="conanbuild")
        self.run(f'{cc} -o sqlite3_analyzer sqlite3_analyzer.c -I{tcl_include} -L{tcl_lib} -ltcl8.6 -ldl -lm -lpthread -lz {cflags}',
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "sqlite3_analyzer", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread", "z"]
        package_bin = os.path.join(self.package_folder, "bin")
        for env in (self.buildenv_info, self.runenv_info):
            env.prepend_path("PATH", package_bin)
