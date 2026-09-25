#!/usr/bin/env python3
"""Conan recipe for pev 0.82 — the PE file analysis toolkit.

Upstream builds with plain Makefiles (no configure/cmake), tree includes
libpe + libudis86 + libfuzzy sources, so the package is self-contained;
the only external hard dependency is OpenSSL (libpe EVP hashing, pesec).

Two portability facts drive this recipe:
1. OHOS devices report `uname -s` = "HarmonyOS". Upstream Makefiles branch
   on `PLATFORM_OS := $(shell uname | cut -d_ -f1)` with no HarmonyOS arm,
   so libpe.so and the output plugins would never be linked. PLATFORM_OS is
   a plain (non-override) make variable → passed on the command line as
   PLATFORM_OS=Linux (same approach as passing an explicit --host triplet
   for config.guess, e.g. abiword-plugin-*).
2. Every tool dlopens its output plugins from a path baked at compile time
   (-DPLUGINSDIR) and exits EXIT_FAILURE when that directory is missing
   (include/common.h PEV_INITIALIZE → plugins_load_all() < 0); pepack reads
   userdb.txt from the baked -DSHAREDIR. Conan moves the package folder
   after the build, so no absolute path baked at build time can survive:
   patch 0002 falls back to executable-relative locations. Plugins keep
   working because the tools are linked with -Wl,--export-dynamic.
3. R26: the device ships a system /lib64/libpe.so. Upstream's libpe must
   therefore not be shipped as a shared object; patch 0003 builds libpe as
   a static archive linked into every tool (R26's static-only remedy — the
   plugins still dlopen fine against the executables' exported symbols).
"""

import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PevConan(ConanFile):
    name = "pev"
    version = "0.82"
    description = "The PE file analysis toolkit (readpe, pehash, pesec, pescan, pepack, pestr, pedis, peres, peldd, rva2ofs, ofs2rva)."
    license = "GPL-2.0-or-later WITH OpenSSL-Link-Exception"
    homepage = "https://github.com/mentebinaria/readpe"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pev requires a POSIX host (Linux or OHOS), not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compilers come from Conan conf, never from shell env/`${CC}`.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"

        openssl = self.dependencies["openssl"]
        cflags = " ".join(
            "-I" + shlex.quote(d) for d in openssl.cpp_info.includedirs
        )
        ldflags = " ".join(
            "-L" + shlex.quote(d) for d in openssl.cpp_info.libdirs
        )
        if ldflags:
            # Keep the packaged binaries resolving the Conan OpenSSL at
            # runtime even without the conanrun environment. The openssl
            # package folder in the cache is stable; pev's own is not (it is
            # moved after the build), which is why nothing of pev itself is
            # baked by absolute path (see patches 0002/0003).
            first_libdir = openssl.cpp_info.libdirs[0]
            ldflags += " -Wl,-rpath," + shlex.quote(first_libdir)

        # R9: -j1. PLATFORM_OS=Linux: `uname -s` is "HarmonyOS" on OHOS and
        # matches no upstream branch (libpe.so/plugins would not be linked).
        # AR is used by patch 0003's static libpe archive.
        self.run(
            "make -j1 PLATFORM_OS=Linux CC={} AR={} CFLAGS={} LDFLAGS={}".format(
                shlex.quote(cc),
                shlex.quote(ar),
                shlex.quote(cflags),
                shlex.quote(ldflags),
            ),
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # 11 CLI tools (src/Makefile PROGS). libpe is statically linked into
        # every tool (patch 0003, R26), so the package ships no libpe*.so —
        # only the dlopen'd output plugins and pepack's signature database.
        build_bin = os.path.join(src, "src", "build")
        for prog in (
            "readpe", "rva2ofs", "ofs2rva", "pehash", "pesec", "pescan",
            "pepack", "pestr", "pedis", "peres", "peldd",
        ):
            copy(self, prog, build_bin, os.path.join(pkg, "bin"), keep_path=False)

        # Output plugins: dlopen'd from the baked PLUGINSDIR (with the
        # executable-relative fallback of patch 0002; the default text
        # output needs its plugin too, so this directory is a runtime hard
        # requirement).
        copy(self, "*_plugin.so", os.path.join(build_bin, "plugins"),
             os.path.join(pkg, "lib", "pev", "plugins"), keep_path=False)

        # pepack packer-signature database (baked SHAREDIR + fallback)
        copy(self, "userdb.txt", os.path.join(src, "src"),
             os.path.join(pkg, "share", "pev"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
