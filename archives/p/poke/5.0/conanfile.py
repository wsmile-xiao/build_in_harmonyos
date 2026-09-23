#!/usr/bin/env python3
"""Conan recipe for GNU poke 5.0 — extensible editor for structured binary data.

Ships the `poke` REPL/CLI, `pokefmt` (template processor) and the static
libpoke plus the runtime pickles (share/poke).

OHOS adaptation notes (see also notes.md):
  * patches/0001: umask 077 -> 022 in configure + jitter/configure so that
    config.status can write its temp files on HMDFS (E011).
  * patches/0002: config.guess/config.sub recognise aarch64-unknown-linux-ohos
    (E007), top-level and jitter.
  * makeinfo is not available on OHOS: the tarball ships the prebuilt manuals
    and the recipe pins their timestamps so `make` never tries to regenerate
    them (the stamp-vti rule would otherwise run mdate-sh, which yields empty
    output on OHOS and makes bash `set` dump the environment into
    version.texi).  MAKEINFO=true is additionally passed to make as a
    command-line override as a belt-and-suspenders guard.
  * bdw-gc: poke's configure looks up the pkg-config module "bdw-gc" but the
    conan package is named "gc"; the flags are injected through the precious
    variables BDW_GC_CFLAGS/BDW_GC_LIBS so pkg-config is bypassed (same
    approach as the guile/2.2.7 recipe in this repo).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PokeConan(ConanFile):
    name = "poke"
    version = "5.0"
    description = "GNU poke, an extensible editor for structured binary data (Poke language REPL, libpoke and pickles)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/poke/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gc/8.2.12")
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: static — the system-name dependencies (gc, readline,
        # ncurses) are merged into the binaries; no .so is shipped.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # libnbd is not available on OHOS: disable the NBD IO space support.
        tc.configure_args.append("--disable-libnbd")
        # readline: point the gnulib havelib probe at the conan package
        # (ncurses, pulled in transitively, is provided by AutotoolsDeps).
        readline = self.dependencies["readline"]
        tc.configure_args.append(
            "--with-libreadline-prefix={}".format(readline.package_folder))
        # bdw-gc: bypass pkg-config ("bdw-gc" vs conan package name "gc").
        gc = self.dependencies["gc"]
        gc_cflags = " ".join(
            "-I{}".format(d) for d in gc.cpp_info.includedirs)
        gc_libs = " ".join(
            "-L{}".format(d) for d in gc.cpp_info.libdirs)
        gc_libs += " " + " ".join(
            "-l{}".format(l) for l in gc.cpp_info.libs)
        tc.configure_args.append("BDW_GC_CFLAGS={}".format(gc_cflags))
        tc.configure_args.append("BDW_GC_LIBS={}".format(gc_libs))
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    # Prebuilt documentation shipped in the tarball: timestamps are pinned in
    # dependency order (stamps -> version files -> manuals) after configure.
    _DOC_STAMPS = [
        "doc/stamp-vti",
        "doc/stamp-1",
        "jitter/doc/stamp-2",
        "jitter/example-vms/jitterlisp/doc/stamp-1",
        "jitter/example-vms/structured/doc/stamp-vti",
    ]
    _DOC_VERSIONS = [
        "doc/version.texi",
        "doc/versionint.texi",
        "jitter/doc/version.texi",
        "jitter/example-vms/jitterlisp/doc/version-jitterlisp.texi",
        "jitter/example-vms/structured/doc/version-structured.texi",
    ]
    _DOC_OUTPUTS = [
        "doc/poke.info",
        "doc/pokeint.info",
        "doc/poke.text",
    ]

    def _pin_prebuilt_docs(self):
        # The portability patches rewrite `configure` (top-level and jitter),
        # and the doc/stamp-* rules depend on it.  makeinfo is missing on
        # OHOS, so any manual rebuild dies with Error 127; the stamp-vti rule
        # would additionally corrupt version.texi via mdate-sh.  Refresh the
        # shipped timestamps in dependency order so `make` never considers the
        # prebuilt manuals out of date.
        for rel in (self._DOC_STAMPS + self._DOC_VERSIONS
                    + self._DOC_OUTPUTS):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                os.utime(path, None)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        self._pin_prebuilt_docs()
        # MAKEINFO=true: command-line override, neutralises any residual
        # makeinfo invocation (propagates to jitter sub-makes via MAKEFLAGS).
        autotools.make(args=["MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        self.cpp_info.libs = ["poke"]
        # Runtime data (pickles, pkl-rt.pk, pokefmt app dir) lives in
        # share/poke; consumers relocate it via POKEDATADIR and friends.
        self.cpp_info.resdirs = ["share"]
