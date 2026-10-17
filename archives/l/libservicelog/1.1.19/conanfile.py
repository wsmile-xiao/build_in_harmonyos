#!/usr/bin/env python3
"""Conan recipe — libservicelog 1.1.19 (IBM Power servicelog library, C).

Pure-C autotools library that stores error events in a sqlite3 database and
exposes a v1 API (servicelog.h) plus a v0.2.9 compat layer. Target is
Power firmware/platform event tooling, but the library itself is plain C +
sqlite3, so it builds unchanged on OHOS with two adjustments:

  * configure.ac hard-requires librtas/librtasevent (AC_CHECK_LIB exits -1).
    The v1 print path never calls into librtasevent (audited: only
    v29_print.c/v29_compat.c reference parse_rtas_event & co, and the test
    suite only drives the v1 API). To close the link without adapting the
    whole librtas package (which is task 8373), the 14 pure-parser .c
    files of librtasevent_src/ are vendored from the official librtas
    2.0.4 tarball (second conandata source) and compiled straight into
    libservicelog. They have zero librtas includes (audited), so no
    librtas package is needed at all.
  * SERVICELOG_PATH is hardcoded to /var/lib/servicelog/servicelog.db.
    patch 0001 adds a SERVICELOG_DB env override (default unchanged),
    mirroring the existing SERVICELOG_TEST env convention in
    repair_action.c; the database schema is self-created by
    servicelog_init(), so any writable path works.

Build facts (audited from the v1.1.19 tarball, 90198 bytes, git tag
v1.1.19 == tarball content, 51 blobs):
  * Library sources: src/{servicelog,addl_data,event,repair_action,
    notify,v29_compat,v29_print,v29_notify_gram,v29_notify_lex}.c
    (the last two ship pre-generated from yacc/flex — no build-time
    toolchain needed).
  * libtool flags: -release 1.1 -version-info 1 -> real file
    libservicelog-1.1.so.1.1.19, SONAME libservicelog-1.1.so.1, dev name
    libservicelog-1.1.so; the pkg-config file advertises -lservicelog, so
    an unversioned libservicelog.so is materialized as well (symlink-free
    copies: HMDFS forbids symlinks, E492-style materialization).
  * Upstream tests: bash runner src/tests/run_tests + 6 scenario scripts
    src/tests/tests/test-00{1..6}* + C driver src/tests/test_libservicelog.c
    + 6 expected outputs src/tests/tests-results/*.result.out +
    libservicelog-ci/{build-fedora-33,build-ubuntu-20.04}.sh = 16 test
    files, 6 functional scenarios (log/dump round-trip per event type,
    timestamp-tolerant comparison). The runner is bash-only and uses
    `diff -y`, so test_package ships a POSIX port + python comparator
    driving the same 6 scenarios with the same tolerance semantics.
  * sqlite3 is the only real dependency; version 3.53.4 from the main
    tree is used (static archive linked into the shared lib).

OHOS notes:
  * Handwritten build (no autotools on device): clang -shared with
    -Wl,-soname; sqlite3.a comes from the sqlite3/3.53.4 conan package.
  * No fork/exec in the tested paths (notify.c is dormant in the suite).
  * DEST_DIR is defined to /usr, matching upstream's exec_prefix default.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# 9 library sources (pre-generated yacc/lex .c included, no toolchain)
_SL_SOURCES = (
    "addl_data.c",
    "event.c",
    "notify.c",
    "repair_action.c",
    "servicelog.c",
    "v29_compat.c",
    "v29_notify_gram.c",
    "v29_notify_lex.c",
    "v29_print.c",
)

# 14 vendored librtasevent sources (librtas 2.0.4 librtasevent_src/,
# exactly librtasevent_la_SOURCES in librtas' Makefile.am; rtas_src_codes.c
# is a noinst_HEADER, textually included — not compiled standalone)
_RTASEVENT_SOURCES = (
    "get_rtas_event.c",
    "print_rtas_event.c",
    "rtas_cpu.c",
    "rtas_dump.c",
    "rtas_epow.c",
    "rtas_io.c",
    "rtas_lri.c",
    "rtas_mem.c",
    "rtas_post.c",
    "rtas_sp.c",
    "rtas_srcfru.c",
    "rtas_v6_misc.c",
    "rtas_vend.c",
    "rtas_hotplug.c",
)

# libtool -release 1.1 -version-info 1
_SONAME = "libservicelog-1.1.so.1"
_REAL_NAME = "libservicelog-1.1.so.1.1.19"
# materialized names: dev link (release convention), unversioned (pc file)
_ALIASES = ("libservicelog-1.1.so", "libservicelog.so")


class LibservicelogConan(ConanFile):
    name = "libservicelog"
    version = "1.1.19"
    package_type = "library"
    description = "IBM Power servicelog library: sqlite3-backed platform event log"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/power-ras/libservicelog"
    url = ""  # CI fills this repository URL

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("sqlite3/3.53.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        for entry in self.conan_data["sources"]:
            # strip_root=False: keep libservicelog-1.1.19/ and
            # librtas-2.0.4/ as separate top-level dirs (both trees
            # contain a Makefile.am; they must not merge).
            get(self, **entry, strip_root=False)

    def _tool(self, key, fallback):
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        value = tools.get(key) if tools else None
        return value or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._tool("c", "clang")
        src_root = os.path.join(self.source_folder, "libservicelog-1.1.19")
        rtas_src = os.path.join(self.source_folder, "librtas-2.0.4", "librtasevent_src")
        build_dir = self.build_folder
        objs = []

        sqlite_dep = self.dependencies["sqlite3"]
        sqlite_info = sqlite_dep.cpp_info
        # cpp_info dirs are package-relative ("include"/"lib"); resolve
        # them against the dependency's package folder (abs or rel).
        def _dep_dir(dirs, fallback):
            d = dirs[0] if dirs else fallback
            return d if os.path.isabs(d) else os.path.join(sqlite_dep.package_folder, d)

        sqlite_inc = _dep_dir(sqlite_info.includedirs, "include")
        sqlite_lib = os.path.join(_dep_dir(sqlite_info.libdirs, "lib"), "libsqlite3.a")

        cflags = [
            "-fPIC",
            "-O2",
            "-I" + sqlite_inc,
            # src_root itself: slog_internal.h includes <servicelog-1/servicelog.h>
            "-I" + src_root,
            "-I" + os.path.join(src_root, "src"),
            "-I" + os.path.join(src_root, "servicelog-1"),
            "-I" + rtas_src,
            "-DDEST_DIR='\"/usr\"'",
        ]

        for src in _SL_SOURCES:
            obj = os.path.join(build_dir, "sl_" + os.path.splitext(src)[0] + ".o")
            self.run("{} {} -c {} -o {}".format(
                cc, " ".join(cflags), os.path.join(src_root, "src", src), obj))
            objs.append(obj)
        for src in _RTASEVENT_SOURCES:
            obj = os.path.join(build_dir, "rte_" + os.path.splitext(src)[0] + ".o")
            self.run("{} {} -c {} -o {}".format(
                cc, " ".join(cflags), os.path.join(rtas_src, src), obj))
            objs.append(obj)

        system_libs = "" if str(self.settings.os) == "Windows" else "-ldl -lpthread -lm"
        self.run("{} -shared {} {} -o {} -Wl,-soname,{} {}".format(
            cc, " ".join(objs), sqlite_lib,
            os.path.join(build_dir, _REAL_NAME), _SONAME, system_libs))

        # HMDFS forbids symlinks: materialize soname/dev/unversioned names
        # as real copies of the same file (E492 pattern, kea precedent).
        for alias in _ALIASES:
            self.run("cp {} {}".format(os.path.join(build_dir, _REAL_NAME),
                                       os.path.join(build_dir, alias)))
        # soname copy as well (also a copy, not a symlink)
        self.run("cp {} {}".format(os.path.join(build_dir, _REAL_NAME),
                                   os.path.join(build_dir, _SONAME)))

    def package(self):
        src_root = os.path.join(self.source_folder, "libservicelog-1.1.19")
        copy(self, "servicelog.h", src=os.path.join(src_root, "servicelog-1"),
             dst=os.path.join(self.package_folder, "include", "servicelog-1"))
        copy(self, "libservicelog.h", src=os.path.join(src_root, "servicelog-1"),
             dst=os.path.join(self.package_folder, "include", "servicelog-1"))
        for lib in (_REAL_NAME, _SONAME) + _ALIASES:
            copy(self, lib, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))
        # pre-built schema DB shipped as data (upstream installs it to
        # /var/lib/servicelog; here it is a template consumers can copy)
        copy(self, "servicelog.db", src=src_root,
             dst=os.path.join(self.package_folder, "share", "libservicelog"))
        # pkg-config file with package-local prefix
        pc = """prefix={prefix}
exec_prefix={{prefix}}
libdir={{prefix}}/lib
includedir={{prefix}}/include

Name: servicelog
Description: Library for access to the system servicelog
Version: 1.1.19
Libs: -L${{libdir}} -lsqlite3 -lservicelog
Cflags: -I${{includedir}}/servicelog-1
""".format(prefix=self.package_folder)
        os.makedirs(os.path.join(self.package_folder, "lib", "pkgconfig"), exist_ok=True)
        with open(os.path.join(self.package_folder, "lib", "pkgconfig",
                               "servicelog-1.pc"), "w") as fh:
            fh.write(pc)
        # upstream test assets for the consumer E2E (test_package)
        utests = os.path.join(self.package_folder, "share", "libservicelog",
                              "upstream-tests")
        os.makedirs(utests, exist_ok=True)
        for name in ("run_tests", "test_libservicelog.c"):
            shutil.copy2(os.path.join(src_root, "src", "tests", name), utests)
        for d in ("tests", "tests-results"):
            shutil.copytree(os.path.join(src_root, "src", "tests", d),
                            os.path.join(utests, d), dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = ["servicelog"]
        self.cpp_info.set_property("cmake_file_name", "libservicelog")
        self.cpp_info.set_property("cmake_target_name", "libservicelog::libservicelog")
        self.cpp_info.set_property("pkg_config_name", "servicelog")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
