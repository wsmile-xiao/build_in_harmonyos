#!/usr/bin/env python3
"""Conan recipe for opensmtpd-table-sqlite — SQLite table backend for OpenSMTPD.

This is a command-line application (not a library) that provides SQLite
database table support for the OpenSMTPD mail server.

Build system: Autotools (configure.ac + Makefile.am + bootstrap)
Dependencies: sqlite3
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpensmtpdTableSqliteConan(ConanFile):
    name = "opensmtpd-table-sqlite"
    version = "1.0.1-r0"
    description = "SQLite table backend for OpenSMTPD"
    license = "MIT"
    homepage = "https://github.com/OpenSMTPD/table-sqlite"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Ensure sqlite3 paths are visible to configure's AC_SEARCH_LIBS
        sqlite3_info = self.dependencies["sqlite3"].cpp_info
        for incdir in sqlite3_info.includedirs:
            tc.extra_cflags.append(f"-I{incdir}")
        for libdir in sqlite3_info.libdirs:
            tc.extra_ldflags.append(f"-L{libdir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Run bootstrap (autoreconf -vfi) to generate configure
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.run("autoreconf -vfi", cwd=self.source_folder)
        # HMDFS workaround: configure/config.status use umask 077 for temp dirs,
        # which fails on HMDFS (Permission denied writing inside 0700 dirs).
        # Patch both configure and (after configure runs) config.status.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        config_status = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(config_status):
            replace_in_file(self, config_status, "umask 077", "umask 022")
            self.run(f"{config_status}", cwd=self.source_folder)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["libexec/smtpd"]
