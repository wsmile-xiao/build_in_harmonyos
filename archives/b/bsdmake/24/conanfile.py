#!/usr/bin/env python3
"""Conan recipe for bsdmake 24 on HarmonyOS PC.

bsdmake is Apple's BSD make tool (derived from NetBSD/FreeBSD make,
used by Apple CoreOS to build). It is a C command-line utility that
compiles 19 source files with a plain cc invocation; the shipped
GNUmakefile targets Apple's Xcode ReleaseControl infrastructure and
the FreeBSD Makefile needs bmake syntax, so the recipe drives the
compile directly (same commands as upstream Makefile.dist).

OHOS-specific adaptations (patches/0001-main.c.patch):
  - Guard <sys/sysctl.h> and the FreeBSD/pc98 sysctlbyname() probe
    with #ifdef __FreeBSD__ (OHOS has no sysctl(3); the pc98 check is
    FreeBSD-only).
  - Replace BSD-only errc() with errno + err() (OHOS libc lacks errc).
  - The source also needs -D'__FBSDID(x)=' -D'__dead2=... so the
    FreeBSD sys/cdefs.h macros missing on OHOS are provided.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BsdmakeConan(ConanFile):
    name = "bsdmake"
    version = "24"
    description = "Apple BSD make tool (NetBSD/FreeBSD derived make)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/apple-oss-distributions/bsdmake"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")

        src = self.source_folder
        objs = []
        c_files = [
            "arch.c", "buf.c", "cond.c", "dir.c", "for.c", "hash.c",
            "hash_tables.c", "job.c", "lst.c", "main.c", "make.c",
            "parse.c", "proc.c", "shell.c", "str.c", "suff.c", "targ.c",
            "util.c", "var.c",
        ]
        cflags = [
            "-O2", "-I" + src,
            "-D'__FBSDID(x)='",
            "-D'__dead2=__attribute__((__noreturn__))'",
            '-DDEFSHELLNAME=\\"sh\\"',
            '-DMAKE_VERSION=\\"5200408120\\"',
        ]
        for c in c_files:
            obj = os.path.join(self.build_folder, c[:-2] + ".o")
            self.run(
                "{cc} {flags} -c {src}/{c} -o {obj}".format(
                    cc=compiler, flags=" ".join(cflags),
                    src=src, c=c, obj=obj,
                )
            )
            objs.append(obj)
        self.run(
            "{cc} {objs} -o {bin}".format(
                cc=compiler, objs=" ".join(objs),
                bin=os.path.join(self.build_folder, "bsdmake"),
            )
        )

    def package(self):
        copy(
            self, "bsdmake",
            src=self.build_folder, dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        # mk/ 子目录下的系统规则文件（sys.mk 等）扁平化复制到 share/mk
        copy(
            self, "mk/*",
            src=self.source_folder, dst=os.path.join(self.package_folder, "share", "mk"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path(
            "MAKESYSPATH", os.path.join(self.package_folder, "share", "mk")
        )
