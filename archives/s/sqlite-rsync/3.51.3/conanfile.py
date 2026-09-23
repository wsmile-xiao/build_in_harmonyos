#!/usr/bin/env python3
"""Conan recipe — sqlite-rsync 3.51.3 (manual build, autosetup incompatible with HMDFS).

sqlite3_rsync is SQLite's remote database synchronization tool. It uses the
autosetup build system, which cannot run on HarmonyOS because /tmp is a
read-only filesystem and the jimsh0 bootstrap TCL interpreter cannot exec
subprocesses on HMDFS. This recipe uses manual clang compilation with the
amalgamation source instead, using the exact RSYNC_OPT flag set from the
upstream main.mk (sqlite3_rsync requires SQLITE_ENABLE_DBPAGE_VTAB: its
protocol is built on the sqlite_dbpage virtual table).

Sources: two downloads required —
  1. sqlite-amalgamation-3510300.zip  → sqlite3.c, sqlite3.h (build products)
  2. sqlite-src-3510300.zip           → tool/sqlite3_rsync.c (canonical source)

Patches: 0001 backports the upstream argv hardening fix (check-in
c84d596b6da2, 2026-05-26) that postdates the 3.51.3 release.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SqliteRsyncConan(ConanFile):
    name = "sqlite-rsync"
    version = "3.51.3"
    description = "SQLite remote database synchronization tool"
    license = "Public-Domain"
    homepage = "https://sqlite.org/rsync.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        # Download amalgamation (sqlite3.c, sqlite3.h) — strip_root to get files directly
        get(self, **self.conan_data["sources"]["amalgamation"],
            strip_root=True, destination="amalgamation")
        # Download full source tree — strip_root to get tool/sqlite3_rsync.c
        get(self, **self.conan_data["sources"]["src"],
            strip_root=True, destination="srctree")

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler path from Conan conf, not shell env
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        # Same flag set as upstream main.mk RSYNC_OPT for sqlite3_rsync:
        #   -DSQLITE_ENABLE_DBPAGE_VTAB -USQLITE_THREADSAFE -DSQLITE_THREADSAFE=0
        #   -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_OMIT_DEPRECATED
        # SQLITE_ENABLE_DBPAGE_VTAB is mandatory: originSide/replicaSide read and
        # write pages through the sqlite_dbpage virtual table; without it every
        # sync fails at runtime with "no such table: sqlite_dbpage".
        defines = (
            "-DSQLITE_ENABLE_DBPAGE_VTAB "
            "-DSQLITE_THREADSAFE=0 "
            "-DSQLITE_OMIT_LOAD_EXTENSION "
            "-DSQLITE_OMIT_DEPRECATED"
        )
        cflags = " ".join(self._get_cflags())

        amalgamation_dir = os.path.join(self.source_folder, "amalgamation")
        rsync_src = os.path.join(self.source_folder, "srctree", "tool", "sqlite3_rsync.c")

        # Step 1: Compile amalgamation source to object file
        self.run(f'"{cc}" -c "{amalgamation_dir}/sqlite3.c" -o sqlite3.o {defines} {cflags}')

        # Step 2: Compile sqlite3_rsync.c (include path for sqlite3.h)
        self.run(f'"{cc}" -c "{rsync_src}" -I"{amalgamation_dir}" -o sqlite3_rsync.o {defines} {cflags}')

        # Step 3: Link into executable
        self.run(f'"{cc}" sqlite3_rsync.o sqlite3.o -o sqlite3_rsync -lpthread -ldl -lm')

    def _get_cflags(self):
        if self.settings.build_type == "Debug":
            return ["-fPIC", "-g"]
        return ["-fPIC", "-O2"]

    def package(self):
        copy(self, "sqlite3_rsync", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # HarmonyOS requires ELF signing before a binary can be executed (E082).
        bin_path = os.path.join(self.package_folder, "bin", "sqlite3_rsync")
        if os.path.exists(bin_path):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f'"{objcopy}" --remove-section .codesign "{bin_path}"', quiet=True)
            self.run(
                f'"{sign_tool}" sign -inFile "{bin_path}" -outFile "{tmp_signed}" '
                f'-selfSign 1',
                quiet=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
