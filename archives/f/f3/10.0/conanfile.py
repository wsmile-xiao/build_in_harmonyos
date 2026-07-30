#!/usr/bin/env python3
"""Conan recipe for f3 (Fight Flash Fraud) v10.0.

f3 is a command-line tool that tests flash cards and USB drives for true capacity.
Build system: plain Makefile (not autotools, not cmake).
On HarmonyOS, argp.h is not available in libc — argp-standalone source is bundled.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class F3Conan(ConanFile):
    name = "f3"
    version = "10.0"
    description = "F3 - Fight Flash Fraud. Test flash cards and USB drives for true capacity."
    license = "GPL-3.0"
    homepage = "https://github.com/AltraMayor/f3"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Bundle argp-standalone source files (no network download during build)
    exports_sources = "extra_sources/argp-standalone/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

        # Get compiler from Conan profile conf
        cc_execs = {}
        try:
            cc_execs = self.conf_info.get("tools.build:compiler_executables") or {}
        except Exception:
            pass
        if not isinstance(cc_execs, dict):
            cc_execs = {}
        cc = cc_execs.get("c", os.environ.get("CC", "clang"))
        ar = os.environ.get("AR", "llvm-ar")

        # On OHOS, argp.h is not in libc — build argp-standalone from bundled source
        if self.settings.os == "OHOS":
            argp_dir = self._build_argp(cc, ar)
            cflags = f"-fPIC -O2 -I{argp_dir}/include"
            ldflags = f"-L{argp_dir}/lib -largp"
        else:
            cflags = "-fPIC -O2"
            ldflags = ""

        # f3 uses a plain Makefile with CC ?= gcc
        # OS=Linux skips the Makefile's argp path logic
        # Run make from source_folder where the Makefile lives
        self.run("make clean 2>/dev/null || true", cwd=self.source_folder)
        self.run(f'make OS=Linux CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" -j1',
                  cwd=self.source_folder)

    def _build_argp(self, cc, ar):
        """Build argp-standalone static library from bundled source files."""
        argp_src = os.path.join(self.source_folder, "extra_sources", "argp-standalone")
        argp_bld = os.path.join(self.build_folder, "argp-bld")
        argp_inst = os.path.join(self.build_folder, "argp-inst")

        # Create build directory and config.h
        os.makedirs(argp_bld, exist_ok=True)

        config_h = (
            "#define HAVE_CONFIG_H 1\n"
            "#define HAVE_UNISTD_H 1\n"
            "#define HAVE_ALLOCA_H 1\n"
            "#define HAVE_MALLOC_H 1\n"
            "#define HAVE_LIMITS_H 1\n"
            "#define HAVE_LIBINTL_H 1\n"
            "#define HAVE_ASPRINTF 1\n"
            "#define HAVE_STRNDUP 1\n"
            "#define HAVE_STRCASECMP 1\n"
            "#define HAVE_DECL_FLOCKFILE 1\n"
            "#define HAVE_DECL_FPUTC_UNLOCKED 1\n"
            "#define HAVE_DECL_FWRITE_UNLOCKED 1\n"
            "#define HAVE_DECL_PUTC_UNLOCKED 1\n"
            "#define _GNU_SOURCE 1\n"
            "#define dgettext(domain, msg) (msg)\n"
            "#define HAVE_GCC_ATTRIBUTE 1\n"
            '#define NORETURN __attribute__ ((__noreturn__))\n'
            '#define PRINTF_STYLE(f, a) __attribute__ ((__format__ (__printf__, f, a)))\n'
            "#define UNUSED __attribute__ ((__unused__))\n"
        )
        with open(os.path.join(argp_bld, "config.h"), "w") as f:
            f.write(config_h)

        src_files = [
            "argp-ba.c", "argp-eexst.c", "argp-fmtstream.c", "argp-help.c",
            "argp-parse.c", "argp-pv.c", "argp-pvh.c", "strchrnul.c", "mempcpy.c",
        ]
        obj_files = []
        for src in src_files:
            obj_path = os.path.join(argp_bld, src.replace(".c", ".o"))
            self.run(
                f'{cc} -I{argp_src} -I{argp_bld} -fPIC -O2 -DHAVE_CONFIG_H '
                f"-Wno-incompatible-function-pointer-types -Wno-int-conversion "
                f"-Wno-implicit-function-declaration -Wno-format "
                f'-c {os.path.join(argp_src, src)} -o {obj_path}'
            )
            obj_files.append(obj_path)

        # Create static library
        lib_path = os.path.join(argp_bld, "libargp.a")
        self.run(f'{ar} rcs {lib_path} {" ".join(obj_files)}')

        # Install header and library
        inc_dir = os.path.join(argp_inst, "include")
        lib_dir = os.path.join(argp_inst, "lib")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy(os.path.join(argp_src, "argp.h"), os.path.join(inc_dir, "argp.h"))
        shutil.copy(lib_path, os.path.join(lib_dir, "libargp.a"))

        return argp_inst

    def package(self):
        # Copy f3write and f3read executables (Makefile creates build/ in source folder)
        copy(self, "f3write", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "f3read", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
