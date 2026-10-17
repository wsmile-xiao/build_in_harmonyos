#!/usr/bin/env python3
"""Conan recipe — mafft 7.525 (multiple sequence alignment program).

MAFFT is a pure-C CLI tool driven by a bash front-end script.  The Makefile
in core/ builds ~30 internal binaries (installed to libexec/mafft/) and
generates the `mafft` wrapper script (installed to bin/) from mafft.tmpl via
sed substitution of the libexec path.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MafftConan(ConanFile):
    name = "mafft"
    version = "7.525"
    description = ("MAFFT — multiple sequence alignment program for amino acid "
                   "or nucleotide sequences")
    license = "BSD-3-Clause"
    homepage = "https://mafft.cbrc.jp/alignment/software/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Internal binaries built from core/Makefile (PROGS variable).
    _PROGS = [
        "dvtditr", "dndfast7", "dndblast", "sextet5", "mafft-distance",
        "pairlocalalign", "multi2hat3s", "pairash", "addsingle",
        "maffttext2hex", "hex2maffttext", "splittbfast", "disttbfast",
        "tbfast", "nodepair", "mafft-profile", "f2cl", "mccaskillwrap",
        "contrafoldwrap", "countlen", "seq2regtable", "regtable2seq",
        "score", "getlag", "dndpre", "setcore", "filter", "replaceu",
        "restoreu", "setdirection", "makedirectionlist", "version",
    ]

    # Algorithm aliases — symlinks to the `mafft` wrapper script.
    _ALIASES = [
        "linsi", "ginsi", "einsi", "fftns", "fftnsi", "nwns", "nwnsi",
        "mafft-linsi", "mafft-ginsi", "mafft-einsi", "mafft-fftns",
        "mafft-fftnsi", "mafft-nwns", "mafft-nwnsi",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        core = os.path.join(self.source_folder, "core")

        # R33: get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        # OHOS has no /bin/bash; the mafft wrapper script (generated from
        # mafft.tmpl) must use the OHOS bash path.  Patch the template's
        # shebang before `make` runs sed to generate the final script.
        if self.settings.os == "OHOS":
            mafft_tmpl = os.path.join(core, "mafft.tmpl")
            self.run("sed -i '1s|#!.*|#!/data/service/hnp/bin/bash|' '"
                     + mafft_tmpl + "'")

        # PREFIX is still needed by make for LIBDIR/BINDIR (install paths and
        # the mafft-profile / mafft-distance symlinks).  The mafft wrapper
        # script itself no longer hardcodes PREFIX — see the
        # 0001-mafft-relocatable-libdir patch which replaces _LIBDIR with a
        # runtime path derived from $0, making the package relocatable.
        prefix = self.package_folder
        self.run('make -C "{}" CC="{}" PREFIX="{}" -j1'.format(core, cc, prefix))

    def package(self):
        core = os.path.join(self.source_folder, "core")
        prefix = self.package_folder
        libdir = os.path.join(prefix, "libexec", "mafft")
        bindir = os.path.join(prefix, "bin")

        # Internal binaries → libexec/mafft/
        for prog in self._PROGS:
            copy(self, prog, core, libdir, keep_path=False)

        # Perl helper scripts → libexec/mafft/
        copy(self, "mafftash_premafft.pl", core, libdir, keep_path=False)
        copy(self, "seekquencer_premafft.pl", core, libdir, keep_path=False)

        # User-facing scripts → bin/
        copy(self, "mafft", core, bindir, keep_path=False)
        copy(self, "mafft-homologs.rb", core, bindir, keep_path=False)
        copy(self, "mafft-sparsecore.rb", core, bindir, keep_path=False)

        for prog in self._PROGS:
            os.chmod(os.path.join(libdir, prog), 0o755)
        for name in ("mafftash_premafft.pl", "seekquencer_premafft.pl"):
            os.chmod(os.path.join(libdir, name), 0o755)
        for name in ("mafft", "mafft-homologs.rb", "mafft-sparsecore.rb"):
            os.chmod(os.path.join(bindir, name), 0o755)

        # Algorithm aliases (symlinks to `mafft` in the same bin/ dir).
        for alias in self._ALIASES:
            link_path = os.path.join(bindir, alias)
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink("mafft", link_path)

        # mafft-profile and mafft-distance are in libexec; create bin/
        # symlinks so they can be called directly (matches upstream install).
        for name in ("mafft-profile", "mafft-distance"):
            link_path = os.path.join(bindir, name)
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink("../libexec/mafft/" + name, link_path)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
