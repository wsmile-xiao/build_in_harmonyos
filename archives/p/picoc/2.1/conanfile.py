#!/usr/bin/env python3
"""Conan recipe — picoc 2.1 (Makefile, CLI tool).

picoc (PicoC) is a very small C interpreter for scripting (feature-frozen
upstream v2.1, "New BSD" = BSD-3-Clause). Build system: plain Makefile, no
configure script. The default UNIX host build enables USE_READLINE and links
GNU readline; on OHOS/musl, three portability issues are fixed by
patches/0001-cstdlib-stdio.c.patch / 0002-cstdlib-string.c.patch / 0003-cstdlib-unistd.c.patch (see manifest.yaml knowledge_gained).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class PicocConan(ConanFile):
    name = "picoc"
    version = "2.1"
    description = "A very small C interpreter for scripting"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/zsaleeba/picoc"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GNU readline: interactive line editing (upstream LIBS=-lreadline).
        self.requires("readline/8.3")
        # readline is built static (system-name lib, R26) and needs the
        # ncursesw termcap symbols at final link time, so link them too.
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler must come from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Collect include/lib dirs of the conan-provided readline + ncurses
        inc_flags = []
        lib_flags = []
        for dep_name in ("readline", "ncurses"):
            dep = self.dependencies.get(dep_name)
            if not dep:
                continue
            for d in dep.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(dep.package_folder, d)}")
            for d in dep.cpp_info.libdirs:
                lib_flags.append(f"-L{os.path.join(dep.package_folder, d)}")

        opt = {
            "Debug": "-O0 -g",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")

        # Upstream Makefile assigns CFLAGS and LIBS with '=', so command-line
        # values fully replace the file content. Keep -DUNIX_HOST (selects
        # platform_unix.c and defines USE_READLINE in platform.h).
        cflags = f"-Wall -pedantic -DUNIX_HOST {opt} {' '.join(inc_flags)}"
        libs = f"{' '.join(lib_flags)} -lreadline -lncursesw -lm"

        # R9: always -j1
        self.run(
            f'make CC={cc} CFLAGS="{cflags}" LIBS="{libs}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # picoc is a single self-contained interpreter executable
        copy(self, "picoc", self.source_folder, os.path.join(self.package_folder, "bin"))
        # README carries the upstream license text (New BSD)
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs=[]
