#!/usr/bin/env python3
"""Conan recipe - ne 3.3.4 (The Nice Editor).

Upstream: https://github.com/vigna/ne
ne is a free (GPL'd) text editor for Unix terminals, easy to use for the
beginner, but powerful and fully configurable for the wizard.

Build system: plain makefile (src/makefile), no configure step.
Default build uses terminfo via ncurses; ne links ncursesw statically
(conan ncurses/6.4, built --without-shared per R4/R26) and ships the
terminfo database in share/terminfo so it works on HarmonyOS PC where
/usr/share/terminfo is incomplete.

The generated sources (hash.c/names.c/enums.h/help.c/ext.c/version.h)
are fetched as a second source (conandata "generated_sources" entry,
gitcode raw-branch tarball, same pattern as clp 1.17.10 clp-src-raw):
upstream generates them from ne.texinfo using makeinfo + perl
info2src.pl, but CI workers have no texinfo, so the files are
pre-generated and hosted on a dedicated branch of this repository
instead of shipping a ~4000-line text patch in the PR diff (keeps the
reviewable diff small). They are downloaded in source() with the
sha256 from conandata.yml verified, then copied into src/ of the
extracted source tree.

R32: settings.os must check in ("Linux", "OHOS").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NeConan(ConanFile):
    name = "ne"
    version = "3.3.4"
    description = "ne, the nice editor - easy to use, powerful and fully configurable terminal text editor"
    license = "GPL-3.0"
    homepage = "https://github.com/vigna/ne"
    url = "https://github.com/vigna/ne"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ne uses terminfo via ncurses (default build). ncursesw (wide char)
        # static build per R4/R26 (--without-shared in ncurses recipe).
        self.requires("ncurses/6.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ne is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Pre-generated sources fetched as a second source (conandata
        # "generated_sources" entry): the 9 files upstream generates from
        # ne.texinfo via makeinfo + info2src.pl (gitignored upstream, absent
        # from the tag tarball; CI workers have no texinfo). The tarball is
        # hosted on the ne-src-raw branch of this repository (raw.gitcode.com
        # archive URL, same pattern as clp 1.17.10 clp-src-raw) — sha256 is
        # verified by get(). After strip_root the layout is src/<file>, copy
        # the files into the extracted ne source tree.
        gen = self.conan_data.get("generated_sources", {})
        if gen:
            tmpdir = os.path.join(self.source_folder, "_gen")
            get(self, **gen, destination=tmpdir, strip_root=True)
            copy(self, "*.c", src=os.path.join(tmpdir, "src"),
                 dst=os.path.join(self.source_folder, "src"))
            copy(self, "*.h", src=os.path.join(tmpdir, "src"),
                 dst=os.path.join(self.source_folder, "src"))
        # R3: remaining patches (0002) declared in conandata.yml
        apply_conandata_patches(self)

    def build(self):
        # Plain makefile build (no configure). Compiler comes from the Conan
        # profile conf (R33: never rely on shell env vars; read them from
        # self.conf explicitly).
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or "clang"
        ncurses = self.dependencies["ncurses"]
        ninc = os.path.join(ncurses.package_folder, "include")
        nlib = os.path.join(ncurses.package_folder, "lib")
        # basic_layout copies patched sources next to the build folder root
        # (the dir containing build-release/ also holds src/). Locate src/
        # robustly either at build_folder or one level up.
        cand = [os.path.join(self.build_folder, "src"),
                os.path.join(self.build_folder, os.pardir, "src")]
        src_dir = next((c for c in cand if os.path.isdir(c)), None)
        if not src_dir:
            raise ConanInvalidConfiguration("ne src/ directory not found in " + self.build_folder)
        # makefile: CC, NE_GLOBAL_DIR, OPTS (extra cflags), LIBS (extra libs)
        # LIBS is appended by the link rule: $(CC) ... $^ $(LIBS) $(OPTS) -lm
        # NE_GLOBAL_DIR is where ne looks for system-wide syntax/macros at
        # runtime; the conan package ships them in share/ne so point there.
        global_dir = os.path.join(self.package_folder, "share", "ne")
        self.run(
            'make -C "%s" -j2 CC=%s NE_GLOBAL_DIR=%s '
            'OPTS="-I%s" LIBS="-L%s -lncursesw"' % (src_dir, cc, global_dir, ninc, nlib),
            env="conanbuild",
        )

    def package(self):
        # Sources live next to build folder root (see build()); binary is
        # produced in src/.
        pkg_src = os.path.dirname(os.path.abspath(self.build_folder))
        # binary
        copy(self, "ne", src=os.path.join(pkg_src, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        # syntax files / macros / global dir content
        copy(self, "*.jsf", src=os.path.join(pkg_src, "syntax"),
             dst=os.path.join(self.package_folder, "share", "ne", "syntax"))
        copy(self, "*", src=os.path.join(pkg_src, "macros"),
             dst=os.path.join(self.package_folder, "share", "ne", "macros"))
        copy(self, "extensions", src=pkg_src,
             dst=os.path.join(self.package_folder, "share", "ne"))
        # man page + docs
        copy(self, "ne.1", src=os.path.join(pkg_src, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README.md", src=pkg_src,
             dst=os.path.join(self.package_folder, "share", "doc", "ne"))
        # terminfo database from ncurses dependency (ne needs it at runtime;
        # HarmonyOS PC has only a minimal /usr/share/terminfo)
        ncurses = self.dependencies["ncurses"]
        tinfo_src = os.path.join(ncurses.package_folder, "share", "terminfo")
        if os.path.isdir(tinfo_src):
            copy(self, "*", src=tinfo_src,
                 dst=os.path.join(self.package_folder, "share", "terminfo"))

    def package_info(self):
        # ne is a standalone terminal application, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # Ensure ne binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # terminfo database shipped with the package (TERMINFO takes
        # precedence over /usr/share/terminfo; TERMINFO_DIRS is a fallback
        # search list for ncurses >= 6)
        terminfo = os.path.join(self.package_folder, "share", "terminfo")
        self.runenv_info.define_path("TERMINFO", terminfo)
        self.runenv_info.define_path("TERMINFO_DIRS", terminfo)
