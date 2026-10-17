#!/usr/bin/env python3
"""Conan recipe for uctodata 0.11 — pure datafiles package for the ucto tokeniser.

uctodata ships the *data* consumed by `ucto` (Language Machines, Radboud
University): per-language tokeniser configurations (`tokconfig-*`), abbreviation
lists (`*.abr`), segmentation rules (`*.rule`), quote/EOS tables (`*.quote`,
`*.eos`) and a ligature filter. There is **no source code and no compilation
step** — upstream's `Makefile.am` only runs `install-data`.

The upstream build system is autotools, but `configure.ac` does nothing beyond
generating `config/Makefile` and `uctodata.pc`; regenerating `configure` would
drag in a full autotools bootstrap for zero benefit. The recipe therefore
performs the install itself and reproduces upstream's install layout verbatim:

  config/*            -> share/ucto/          (upstream: configdir=$(datadir)/ucto)
  (generated .pc)     -> lib/pkgconfig/uctodata.pc
                                              (upstream: pkgconfigdir=$(libdir)/pkgconfig)

The .pc file is the *contract*: ucto's configure script resolves the data
directory as `pkg-config --variable=prefix uctodata` + `/share/ucto`
(ucto/configure.ac: UCTODATA_PRE / UCTODATA_DIR). It is therefore regenerated
here with `prefix` pointing at the Conan package folder instead of copying
upstream's `uctodata.pc.in` template — a template copied verbatim would carry
literal `@prefix@` placeholders and silently break every consumer.

License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# The exact payload of upstream `config/Makefile.am`'s `config_DATA` variable,
# which is what `make install-data` copies into $(datadir)/ucto. Keeping the
# literal upstream list (rather than a language/lookup heuristic) is deliberate:
# the abbreviation lists do not cover the same languages as the tokeniser
# configs — there is `tokconfig-ita` but no `ita.abr`, and Dutch ships
# `nld_afk.abr` rather than `nld.abr`. A "one .abr per language" assumption
# would produce a recipe that never passes its own completeness check.
TOKCONFIGS = [
    "tokconfig-eng", "tokconfig-eng-twitter", "tokconfig-nld", "tokconfig-fra",
    "tokconfig-ita", "tokconfig-spa", "tokconfig-por", "tokconfig-deu",
    "tokconfig-swe", "tokconfig-nld-twitter", "tokconfig-nld-sonarchat",
    "tokconfig-tur", "tokconfig-nld-withplaceholder", "tokconfig-nld-historical",
    "tokconfig-fry", "tokconfig-rus", "tokconfig-generic",
]
ABBREVIATIONS = ["nld_afk.abr", "spa.abr", "por.abr", "tur.abr", "fry.abr",
                 "rus.abr", "eng.abr", "swe.abr", "fra.abr", "deu.abr"]
RULES = ["e-mail.rule", "smiley.rule", "url.rule"]
TABLES = ["standard-quotes.quote", "exotic-quotes.quote",
          "standard-eos.eos", "exotic-eos.eos", "ligatures.filter"]
# 17 + 10 + 3 + 5 = 35 installed data files (config/Makefile.am also lists
# Makefile.am itself via EXTRA_DIST — that one is not installed).
DATA_FILES = TOKCONFIGS + ABBREVIATIONS + RULES + TABLES


class UctodataConan(ConanFile):
    name = "uctodata"
    version = "0.11"
    description = ("Datafiles for the ucto tokeniser — per-language tokeniser "
                   "configurations, abbreviation lists, segmentation rules and "
                   "quote/EOS tables for 11+ languages")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/LanguageMachines/uctodata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure data package: no compilation, no libraries, no executables.
    # Upstream README.md states explicitly: "uctodata is architecture independent."
    package_type = "unknown"
    # Data packages are architecture independent; no settings are declared so the
    # package ID is stable across profiles (matches adwaita-fonts-mono, festvox-*).

    _datadir = os.path.join("share", "ucto")
    _pkgconfigdir = os.path.join("lib", "pkgconfig")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # No compilation. Assert that the upstream payload is complete so that a
        # future tarball change fails here instead of producing a data package
        # that is quietly missing a language.
        config_dir = os.path.join(self.source_folder, "config")
        if not os.path.isdir(config_dir):
            raise ConanException(f"config/ directory missing from source: {config_dir}")

        missing = [n for n in DATA_FILES if not os.path.isfile(os.path.join(config_dir, n))]
        if missing:
            raise ConanException(
                f"uctodata {self.version} payload incomplete, missing {len(missing)} "
                f"of {len(DATA_FILES)} file(s): {missing}")

        # Guard against empty data files (a truncated tarball would still extract).
        empty = [n for n in DATA_FILES if os.path.getsize(os.path.join(config_dir, n)) == 0]
        if empty:
            raise ConanException(f"zero-length data files in payload: {empty}")

    def package(self):
        copy(self, "AUTHORS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # Reproduce `make install-data` exactly: only config_DATA members are
        # installed, so Makefile.am must not leak into the package.
        config_dir = os.path.join(self.source_folder, "config")
        dest_dir = os.path.join(self.package_folder, self._datadir)
        for name in DATA_FILES:
            copy(self, name, src=config_dir, dst=dest_dir)

        # ucto discovers uctodata via pkg-config; the generated file must carry the
        # real prefix, so upstream's .pc.in template is expanded here.
        pc_dir = os.path.join(self.package_folder, self._pkgconfigdir)
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "uctodata.pc"), "w", encoding="utf-8") as handle:
            handle.write(
                f"prefix={self.package_folder}\n"
                "exec_prefix=${prefix}\n"
                "\n"
                "Name: uctodata\n"
                f"Version: {self.version}\n"
                "Description: datafiles for ucto\n"
            )

    def package_info(self):
        # Data-only package: expose the data root for consumers that honour
        # cpp_info.resdirs, and keep the pkg-config name aligned with the .pc file
        # so that `pkg_config` generator users find the data directory contract.
        self.cpp_info.resdirs = [self._datadir]
        # A data package installs no headers, libraries or executables, so every
        # default cpp_info directory must be cleared. Leaving the `["include"]` /
        # `["lib"]` / `["bin"]` defaults makes CMakeDeps emit phantom paths into
        # the imported target's INTERFACE_INCLUDE_DIRECTORIES, and consumers fail
        # at CMake generate time with
        #   Imported target "uctodata::uctodata" includes non-existent path
        # (downstream frog 0.34 full-chain test). Declaring them empty keeps the
        # exported target honest while `pkg_config_name` still publishes the
        # prefix contract that ucto resolves its data directory through.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("pkg_config_name", "uctodata")
