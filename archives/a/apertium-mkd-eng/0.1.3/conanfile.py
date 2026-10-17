#!/usr/bin/env python3
"""Conan recipe for apertium-mkd-eng 0.1.3.

Apertium linguistic data for Macedonian-English translation.
This is a pure data package — the source contains .dix, .t1x, .t2x, .t3x,
.rlx, .lex, .prob, .acx, modes.xml and other linguistic data files.

The upstream Makefile.am uses apertium tools (lt-comp, cg-comp,
apertium-preprocess-transfer, etc.) to compile .dix → .bin files.
Since the apertium core engine is not yet published to the OHOS
制品仓, we package the raw linguistic data files directly. The
.bin compiled forms are text-based caches produced by the apertium
toolchain at build time; downstream consumers with the apertium
core installed can regenerate them as needed.

Build system: autotools (configure.ac + Makefile.am + autogen.sh)
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file


class ApertiumMkdEngConan(ConanFile):
    name = "apertium-mkd-eng"
    version = "0.1.3"
    description = "Apertium linguistic data for Macedonian-English translation"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/apertium/apertium-mkd-eng"
    url = "https://github.com/apertium/apertium-mkd-eng"
    topics = ("apertium", "translation", "macedonian", "english", "nlp",
              "linguistic-data")
    package_type = "header-library"
    settings = "os", "arch"
    no_copy_source = True

    @property
    def _data_subdir(self):
        """Subdirectory under share/ for this language pair."""
        return os.path.join("share", "apertium", "apertium-mkd-eng")

    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_folder)

    def requirements(self):
        # apertium core engine (lt-comp, lt-proc, cg-comp, etc.) is a
        # runtime dependency, not yet published to ohpcd. Declared in
        # notes.md. This package ships only the linguistic data files.
        pass

    def layout(self):
        # Basic layout — no build folder needed for a data-only package
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def build(self):
        """
        Build step for apertium-mkd-eng.

        The upstream build uses lt-comp/cg-comp/apertium-preprocess-transfer
        (from the apertium core package) to compile .dix → .bin. Since the
        apertium core is not available on OHOS yet, we skip the compilation
        step and install the raw linguistic data files directly.

        The raw data files (.dix, .t1x, .t2x, .t3x, .rlx, .lex, .prob, .acx,
        modes.xml) are the authoritative source — the .bin files are just
        pre-compiled caches. Downstream consumers with the apertium core
        installed can regenerate .bin files as needed.

        We also validate key data files exist and are non-empty.
        """
        source_dir = self.source_folder
        data_files = [
            "apertium-mkd-eng.eng.dix",
            "apertium-mkd-eng.mkd-eng.dix",
            "apertium-mkd-eng.mkd.dix",
            "apertium-mkd-eng.mkd-eng.t1x",
            "apertium-mkd-eng.mkd-eng.t2x",
            "apertium-mkd-eng.mkd-eng.t3x",
            "apertium-mkd-eng.mkd-eng.rlx",
            "apertium-mkd-eng.mkd-eng.lex",
            "apertium-mkd-eng.post-eng.dix",
            "apertium-mkd-eng.mkd.acx",
            "apertium-mkd-eng.mkd-eng.alpha.dix",
            "modes.xml",
        ]

        # Validate all data files exist and are non-empty
        for fname in data_files:
            fpath = os.path.join(source_dir, fname)
            if not os.path.isfile(fpath):
                raise RuntimeError(
                    f"Required data file '{fname}' not found in source")
            if os.path.getsize(fpath) == 0:
                raise RuntimeError(
                    f"Required data file '{fname}' is empty")

        # Also check prob files
        for fname in ["mkd-eng.prob", "eng-mkd.prob"]:
            fpath = os.path.join(source_dir, fname)
            if not os.path.isfile(fpath):
                raise RuntimeError(
                    f"Required prob file '{fname}' not found in source")

    def package(self):
        """
        Install linguistic data files to share/apertium/apertium-mkd-eng/.

        We copy all linguistic data files directly from source. No .bin
        compilation is performed (requires apertium core tools).
        """
        source_dir = self.source_folder
        dest_dir = os.path.join(self.package_folder, self._data_subdir)

        # Core dictionary files
        data_files = [
            "apertium-mkd-eng.eng.dix",
            "apertium-mkd-eng.mkd-eng.dix",
            "apertium-mkd-eng.mkd.dix",
            "apertium-mkd-eng.mkd-eng.t1x",
            "apertium-mkd-eng.mkd-eng.t2x",
            "apertium-mkd-eng.mkd-eng.t3x",
            "apertium-mkd-eng.mkd-eng.rlx",
            "apertium-mkd-eng.mkd-eng.lex",
            "apertium-mkd-eng.mkd-eng.lrx",
            "apertium-mkd-eng.post-eng.dix",
            "apertium-mkd-eng.mkd.acx",
            "apertium-mkd-eng.mkd-eng.alpha.dix",
            "modes.xml",
            "lexchoicebil.xsl",
            "mkd-eng.prob",
            "eng-mkd.prob",
            "prep-smoothing",
        ]

        for fname in data_files:
            src = os.path.join(source_dir, fname)
            if os.path.isfile(src):
                copy(self, fname, source_dir, dest_dir)

    def package_info(self):
        """
        Package info for apertium-mkd-eng linguistic data.

        This is a header-library type package (pure data, no compiled
        output). We set includedirs=[] and libdirs=[] to indicate no
        standard library artifacts. The data files reside under
        share/apertium/apertium-mkd-eng/.
        """
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]

        # Define a dependency variable for downstream consumers
        self.cpp_info.set_property("apertium_data_dir",
                                   self._data_subdir)
