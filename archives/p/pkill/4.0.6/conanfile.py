#!/usr/bin/env python3
"""Conan recipe — pkill 4.0.6

pkill is part of the procps-ng suite. It is built from src/pgrep.c
(same source as pgrep) and links against libproc2 (the procps-ng library).

Source: Official release tarball from SourceForge (includes pre-generated
configure script, no autoreconf needed).

On HarmonyOS (musl libc), the autotools config.status fails due to HMDFS
filesystem permission issues. This recipe uses manual compilation instead.

R26: Terminal tools must be statically linked.
R38: Produces executable (pkill), needs commands.json.
"""
import os
import glob
import json as _json

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PkillConan(ConanFile):
    name = "pkill"
    version = "4.0.6"
    description = "Send signal to processes by name (from procps-ng)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/procps-ng/procps"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # Manual build, no autotools toolchain needed

    def _get_cc(self):
        """Get C compiler from Conan profile conf (R33)."""
        cc = "clang"
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        if ce:
            if isinstance(ce, str):
                ce = _json.loads(ce)
            cc = ce.get("c", "clang")
        return cc

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        bld = self.build_folder
        cc = self._get_cc()

        # Create minimal config.h (autotools config.status fails on HMDFS)
        config_h = os.path.join(bld, "config.h")
        with open(config_h, "w") as f:
            f.write("""/* Minimal config.h for pkill manual build on HarmonyOS */
#define PACKAGE "procps-ng"
#define PACKAGE_NAME "procps-ng"
#define PACKAGE_STRING "procps-ng 4.0.6"
#define PACKAGE_VERSION "4.0.6"
#define VERSION "4.0.6"
#define HAVE_LOCALE_H 1
#define HAVE_LANGINFO_H 1
#define HAVE_STDBOOL_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_UNISTD_H 1
#define HAVE_WCHAR_H 1
#define HAVE_MEMORY_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_FCNTL_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_LIMITS_H 1
#define HAVE_SIGNAL_H 1
#define HAVE_REGEX_H 1
#define HAVE_FORK 1
#define HAVE_VFORK 1
#define HAVE_WORKING_FORK 1
#define HAVE_WORKING_VFORK 1
#define HAVE_MMAP 1
#define HAVE_STRCASECMP 1
#define HAVE_STRNCASECMP 1
#define HAVE_STRDUP 1
#define HAVE_STRNDUP 1
#define HAVE_MEMSET 1
#define HAVE_MEMMOVE 1
#define HAVE_SETLOCALE 1
#define HAVE_STRTOL 1
#define HAVE_STRTOUL 1
#define HAVE_GETHOSTNAME 1
#define HAVE_GETPAGESIZE 1
#define HAVE_ALLOCA 1
#define HAVE_ISWPRINT 1
#define HAVE_WCWIDTH 1
#define HAVE_ERR_H 1
#define HAVE_PROGRAM_INVOCATION_NAME 1
#define HAVE_PROGRAM_INVOCATION_SHORT_NAME 1
extern char *program_invocation_name;
extern char *program_invocation_short_name;
""")

        # Compiler settings — all include paths relative to source folder
        cflags = '-O2 -fPIC -I"{}" -I"{}/local" -I"{}/library/include" -I"{}"'.format(
            src, src, src, bld)

        # Compile local source files (needed by pkill)
        local_files = [
            "local/fileutils.c",
            "local/signals.c",
            "local/strutils.c",
        ]

        # Compile library source files (libproc2)
        # Skip files that fail on musl (meminfo.c, vmstat.c — hsearch_data)
        lib_files = []
        for cfile in sorted(glob.glob(os.path.join(src, "library/*.c"))):
            basename = os.path.basename(cfile)
            if basename in ("meminfo.c", "vmstat.c"):
                continue
            lib_files.append(cfile)

        all_sources = [os.path.join(src, f) for f in local_files] + lib_files + [os.path.join(src, "src/pgrep.c")]

        all_objs = []
        for srcfile in all_sources:
            basename = os.path.basename(srcfile).replace(".c", ".o")
            objpath = os.path.join(bld, basename)
            all_objs.append(objpath)
            self.run('{} {} -c "{}" -o "{}"'.format(cc, cflags, srcfile, objpath))

        # Link pkill as static binary
        pkill_bin = os.path.join(bld, "pkill")
        obj_args = " ".join('"{}"'.format(o) for o in all_objs)
        self.run('{} -static -o "{}" {} -lpthread -lm'.format(cc, pkill_bin, obj_args))

    def package(self):
        copy(self, "pkill", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
