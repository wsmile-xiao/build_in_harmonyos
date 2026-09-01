#!/usr/bin/env python3
"""Conan recipe for pg_dump 18.3 — PostgreSQL database dump utility.

Builds from the official PostgreSQL source tree, producing:
  - pg_dump, pg_dumpall, pg_restore (command-line tools)
  - pg_config (build configuration utility)
  - libpq (PostgreSQL client library)
  - libpgcommon, libpgport (internal support libraries)

OHOS platform adaptations applied via patch:
  - SysV shared memory bypass (shmget/shmat SIGSYS)
  - hmdfs filesystem permission relaxation
  - DSM forced to mmap (shm_open detected but SIGSYS at runtime)
  - getpwuid fallback for users not in /etc/passwd
  - Unix-domain socket disabled (EPERM on OHOS)
  - mkdir permission correction for hmdfs S-bit issue
  - configure umask 077->067 fix for hmdfs temp directories
"""
import os
import multiprocessing

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PgDumpConan(ConanFile):
    name = "pg_dump"
    version = "18.3"
    description = "PostgreSQL database dump utility (pg_dump, pg_dumpall, pg_restore)"
    license = "PostgreSQL"
    homepage = "https://www.postgresql.org"
    url = "https://github.com/postgres/postgres"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-icu",
            "--without-readline",
            "--without-zlib",
            "--without-openssl",
        ])
        # OHOS: config.guess cannot compile test programs, must specify build type
        if self.settings.os in ("Linux", "OHOS"):
            arch = str(self.settings.arch)
            if arch == "armv8":
                arch = "aarch64"
            tc.configure_args.append(f"--build={arch}-unknown-linux-ohos")
        tc.generate()

    def build(self):
        # Set TMPDIR for OHOS (E002: /tmp is read-only on OHOS)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=[f"-j{multiprocessing.cpu_count() or 1}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pq", "pgcommon", "pgport"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
