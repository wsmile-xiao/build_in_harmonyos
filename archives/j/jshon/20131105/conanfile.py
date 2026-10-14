#!/usr/bin/env python3
"""Conan recipe for jshon 20131105 — JSON parsing on the command line.

Upstream: https://github.com/keenerd/jshon (MIT, Kyle Keen 2010-2013)
Build system: plain GNU Makefile (implicit rules only, no configure).

OHOS portability notes
----------------------
1. ``jshon.c`` uses the legacy ``uint`` typedef but never includes
   ``<sys/types.h>``. Vanilla-musl systems reach the typedef transitively via
   ``sys/stat.h``; the OHOS musl sysroot's ``sys/stat.h`` uses
   ``bits/alltypes.h`` instead, so the include chain never reaches it and the
   upstream ``-Werror`` build dies with ``unknown type name 'uint'`` at the
   ``mapping`` struct (plus a knock-on -Wsign-compare once uint falls back to
   int). ``patches/0001`` adds the missing include after the file's own
   ``#define _GNU_SOURCE`` (which unlocks the typedef guard); same root cause
   and same fix as Alpine's ``missing-typesh.patch``.
2. The OHOS clang wrapper injects ``-Wl,--code-sign`` (linker self-signing)
   into every invocation. At compile time that flag is unused, so clang emits
   ``-Wunused-command-line-argument`` — fatal under upstream ``-Werror``
   (repo precedents: aesfix, asterisk). Suppressed by appending
   ``-Wno-unused-command-line-argument`` via the Makefile's own ``${CFLAGS}``
   tail (env CFLAGS), so all upstream flags stay intact.
3. Upstream declares 6 helper functions K&R-style ``()``; clang 15 flags them
   ``-Wstrict-prototypes`` under ``-Werror``. Suppressed the same way
   (repo precedent: asmotor), keeping the source pristine.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JshonConan(ConanFile):
    name = "jshon"
    version = "20131105"
    description = (
        "JSON parsing on the command line: a stack-based filter pipeline to "
        "extract, edit and create JSON from stdin or files"
    )
    license = "MIT"
    homepage = "https://github.com/keenerd/jshon"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # jshon's only third-party dependency (json_loads/json_dumps/...);
        # reuse the repo package instead of vendoring (W0 conclusion).
        self.requires("jansson/2.15.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan conf, never from bare shell vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # jansson include/lib dirs (repo idiom, cf. cmatrix/ncurses).
        jansson = self.dependencies["jansson"]
        inc_dir = jansson.cpp_info.aggregated_components().includedirs[0]
        lib_dir = jansson.cpp_info.aggregated_components().libdirs[0]

        # Upstream Makefile: `CFLAGS := -std=c99 -Wall -pedantic -Wextra -Werror
        # ${CFLAGS}` — env CFLAGS lands *after* -Werror, so the -Wno flags below
        # win without touching the Makefile or dropping any upstream flag:
        #   * -Wno-unused-command-line-argument: the OHOS clang wrapper injects
        #     -Wl,--code-sign, unused (and fatal under -Werror) at compile time;
        #   * -Wno-strict-prototypes: 6 K&R `()` declarations vs clang 15.
        # CFLAGS must go through the environment (a `make CFLAGS=...` command
        # line would replace the upstream flags entirely). CPPFLAGS/LDFLAGS are
        # not set by the Makefile and flow into make's built-in compile/link
        # rules; CC is pinned on the make command line.
        env = Environment()
        env.define("CFLAGS", "-Wno-unused-command-line-argument -Wno-strict-prototypes")
        env.define("CPPFLAGS", f"-I{inc_dir}")
        env.define("LDFLAGS", f"-L{lib_dir}")
        with env.vars(self).apply():
            self.run(f'make CC="{cc}" -j1 jshon', cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "jshon", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "jshon.1", src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # Upstream installs the binary 0755; ensure the exec bit survives packaging.
        os.chmod(os.path.join(self.package_folder, "bin", "jshon"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
