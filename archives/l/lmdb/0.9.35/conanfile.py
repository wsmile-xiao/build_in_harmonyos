#!/usr/bin/env python3
"""Conan recipe for LMDB 0.9.35 (Lightning Memory-Mapped Database).

LMDB uses a plain Makefile (no autotools, no cmake).
OpenHarmony musl libc lacks robust mutex support, so MDB_USE_ROBUST=0 is required.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import download, unzip, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LmdbConan(ConanFile):
    name = "lmdb"
    version = "0.9.35"
    description = "Lightning Memory-Mapped Database Manager"
    license = "OpenLDAP"
    homepage = "https://git.openldap.org/openldap/openldap"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # GitHub API tarball has no .tar.gz extension, so conan's get()
        # misidentifies the format. Download with explicit .tar.gz filename.
        # The LMDB source lives under libraries/liblmdb/ — promote to root.
        src = self.conan_data["sources"]
        archive = os.path.join(self.source_folder, "lmdb-0.9.35.tar.gz")
        # E017/CI handles ghfast.top mirror injection
        download(self, src["url"], archive, sha256=src["sha256"])
        unzip(self, archive, strip_root=True)
        os.unlink(archive)

        # Promote libraries/liblmdb/* to source root
        nested = os.path.join(self.source_folder, "libraries", "liblmdb")
        if os.path.isdir(nested):
            for item in os.listdir(nested):
                src_path = os.path.join(nested, item)
                dst_path = os.path.join(self.source_folder, item)
                shutil.move(src_path, dst_path)
            shutil.rmtree(os.path.join(self.source_folder, "libraries"))

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # OpenHarmony musl libc lacks robust mutex support, so MDB_USE_ROBUST=0 is required.
        # On Linux/glibc, keep the default robust mutex behavior.
        xcflags = "-DMDB_USE_ROBUST=0" if str(self.settings.os) == "OHOS" else ""

        # Build targets: all (liblmdb.a + tools) + liblmdb.so if shared
        targets = "all"
        if self.options.shared:
            targets += " liblmdb.so"

        # R9: Always use -j1
        make_args = [f"CC={cc}"]
        if xcflags:
            make_args.append(f"XCFLAGS={xcflags}")
        make_args += [targets, "-j1"]

        self.run("make " + " ".join(make_args), cwd=self.source_folder)

    def package(self):
        copy(self, "lmdb.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "liblmdb.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "liblmdb.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Tools
        copy(self, "mdb_stat", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "mdb_copy", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "mdb_dump", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "mdb_load", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["lmdb"]
        self.cpp_info.system_libs = ["pthread"]