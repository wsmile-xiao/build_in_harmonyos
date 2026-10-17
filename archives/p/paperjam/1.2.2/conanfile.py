#!/usr/bin/env python3
"""Conan recipe for paperjam 1.2.2 — plain-Makefile C++ PDF tool.

Upstream: https://mj.ucw.cz/sw/paperjam/ (Martin Mares, GPL-2.0-or-later).
Build: `make paperjam` (only the binary; man pages need a2x/asciidoc and
are intentionally skipped). Links against libqpdf and libpaper.

Dependency note (W0/R36): only qpdf is a Conan requirement (qpdf/12.3.2
has a recipe in this repo). libpaper 1.1.28 in this repo is a legacy
archive without a conanfile (manifest + patches only, not installable via
`conan download`), so it cannot be a Conan requirement. paperjam uses just
three libpaper symbols (paperinfo/paperpswidth/paperpsheight, all in
cmds.cc `paper_spec`), therefore this recipe vendors a minimal
libpaper-compatible shim (vendored/paper.h + vendored/paper.c, static
table of ISO/US paper sizes in PS points) compiled to libpaper.a at build
time. No upstream source patch is needed: the shim directory is added with
CPPFLAGS -I and the archive directory with LDLIBS -L, so the unmodified
`#include <paper.h>` / `-lpaper` resolve to the shim.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class PaperjamConan(ConanFile):
    name = "paperjam"
    version = "1.2.2"
    description = "PaperJam: program for transforming PDF files (re-order/scale/n-up/cropmarks)"
    license = "GPL-2.0-or-later"
    homepage = "https://mj.ucw.cz/sw/paperjam/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    exports = "conandata.yml"

    def export_sources(self):
        # Explicit copy (faiss-proven pattern): attribute glob
        # `exports_sources = "vendored/*"` did not materialise
        # `e/vendored/paper.c` in the Conan cache, so build() failed
        # with `no such file or directory: .../e/vendored/paper.c`.
        # Copy the shim into export_sources_folder instead.
        copy(self, "paper.c", src=os.path.join(self.recipe_folder, "vendored"),
             dst=os.path.join(self.export_sources_folder, "vendored"))
        copy(self, "paper.h", src=os.path.join(self.recipe_folder, "vendored"),
             dst=os.path.join(self.export_sources_folder, "vendored"))

    def requirements(self):
        self.requires("qpdf/12.3.2")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, default):
        # R33: compiler/tools come from Conan conf, never from shell env.
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return conf.get(key, default)

    def build(self):
        cxx = self._tool("cpp", "clang++")
        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")

        # 1) Build the vendored libpaper shim as a static archive.
        # exports_sources live in export_sources_folder (Conan 2), not in
        # recipe_folder (`e/`). Probe all known layouts so cache/local both work.
        shim_candidates = [
            os.path.join(self.export_sources_folder, "vendored"),
            os.path.join(self.source_folder, "vendored"),
            os.path.join(self.recipe_folder, "vendored"),
        ]
        shim_src = next(
            (d for d in shim_candidates
             if os.path.isfile(os.path.join(d, "paper.c"))),
            shim_candidates[0],
        )
        if not os.path.isfile(os.path.join(shim_src, "paper.c")):
            raise Exception(
                "vendored paper.c not found; tried: %s (export_sources=%s)" % (
                    shim_candidates,
                    os.listdir(self.export_sources_folder)
                    if os.path.isdir(self.export_sources_folder) else "missing",
                )
            )
        shim_build = os.path.join(self.build_folder, "vendored-build")
        os.makedirs(shim_build, exist_ok=True)
        self.run(f"{cc} -O2 -Wall -c \"{os.path.join(shim_src, 'paper.c')}\" -o \"{os.path.join(shim_build, 'paper.o')}\"")
        self.run(f"{ar} rcs \"{os.path.join(shim_build, 'libpaper.a')}\" \"{os.path.join(shim_build, 'paper.o')}\"")

        # 2) Collect include/lib dirs of qpdf + its transitive deps.
        inc_dirs = []
        lib_dirs = []
        for _ref, dep in self.dependencies.items():
            try:
                inc_dirs += list(dep.cpp_info.includedirs)
            except Exception:
                pass
            try:
                lib_dirs += list(dep.cpp_info.libdirs)
            except Exception:
                pass
        # Deduplicate while keeping order.
        inc_dirs = list(dict.fromkeys(inc_dirs))
        lib_dirs = list(dict.fromkeys(lib_dirs))

        cppflags = " ".join(["-I" + p for p in inc_dirs] + ["-I" + shim_src])
        ldpaths = " ".join(["-L" + p for p in lib_dirs] + ["-L" + shim_build])
        # HMBS [stale_runtime_library]: OHOS loader ignores LD_LIBRARY_PATH,
        # so embed DT_RPATH (legacy RPATH, not RUNPATH) pointing at the conan
        # dep lib dirs directly in the paperjam binary. musl dynlink only
        # honors DT_RPATH, hence --disable-new-dtags. Pass via LDLIBS because
        # the upstream plain Makefile honours LDLIBS on the link line
        # (LDFLAGS may be ignored); RPATH of the main binary also resolves
        # transitive DT_NEEDED (libjpeg.so.62 pulled in by libqpdf.so).
        rpath_flags = " ".join(
            ["-Wl,--disable-new-dtags"]
            + ["-Wl,-rpath,%s" % p for p in lib_dirs]
        )
        # NOTE: upstream Makefile appends target-specific `LDLIBS += -lqpdf -lpaper`,
        # so command-line LDLIBS keeps our -L paths and still links both libs
        # (duplicated -l flags are harmless). Build only the `paperjam` target:
        # the default `all` also builds man pages and needs a2x/asciidoc.
        # R9: single job on OHOS.
        self.run(
            "make -C \"{src}\" paperjam -j1 CXX=\"{cxx}\" LD=\"{cxx}\" "
            "CPPFLAGS=\"{cppflags}\" LDFLAGS=\"{rpath}\" LDLIBS=\"{ldpaths} -lqpdf -lpaper {rpath}\"".format(
                src=self.source_folder, cxx=cxx, cppflags=cppflags, ldpaths=ldpaths,
                rpath=rpath_flags
            )
        )

    def package(self):
        copy(self, "paperjam", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
