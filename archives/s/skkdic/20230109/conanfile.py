#!/usr/bin/env python3
"""Conan recipe — skkdic 20230109.

skkdic is the standard dictionary of the SKK Japanese input method. The
upstream distribution tarball is a pure-data archive: plain-text SKK
dictionary files (``SKK-JISYO.*``) plus ``ChangeLog`` and licence texts.
No C/C++ code is compiled — the recipe has no ``build()`` method and simply
installs the dictionary files under ``share/skk/``.

Upstream's Makefile regenerates derived dictionaries via ``gawk``/``ruby``/
``emacs`` and the ``skk-dev/tools`` helper programs (``skkdic-sort``,
``skkdic-expr``, ``skkdic2kanadic``, ...). None of those exist in a clean CI
environment, and the distribution tarball already ships every generated file,
so the upstream build steps are intentionally not reproduced. This mirrors
what Debian's own binary ``skkdic`` package does.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class SkkdicConan(ConanFile):
    name = "skkdic"
    version = "20230109"
    description = "skkdic 20230109: SKK standard dictionary (pure data package)"
    license = "GPL-2.0-or-later"
    homepage = "https://skk-dev.github.io/dict/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    # Pure data package: no options, no build() step, no library artefacts.
    # `package_type` is deliberately left unset. It must not be "application"
    # and bindirs must stay empty, otherwise the L0k / R38 gate starts
    # demanding a commands.json manifest, which a dictionary package has no
    # use for. Precedent in this repo: archives/m/mecab-jumandic/7.0-20130310/.

    # Relative location of the installed dictionary tree, published to
    # consumers as a cpp_info property so downstream recipes do not have to
    # hard-code the layout.
    datadir = "share/skk"

    def export_sources(self):
        # No patches for this version (conandata.yml declares `patches: {}`),
        # but conandata.yml itself must travel with the recipe so that
        # source() can read it back from the recipe folder.
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def source(self):
        src = self.conan_data["sources"]
        get(self, **src, strip_root=True)
        self.output.info(f"Source downloaded and SHA256 verified: {src['url']}")

    def package(self):
        src = self.source_folder
        dst = os.path.join(self.package_folder, self.datadir)
        os.makedirs(dst, exist_ok=True)

        # Main dictionary files, shipped at the top level of the tarball.
        for name in sorted(os.listdir(src)):
            if name.startswith("SKK-JISYO.") and os.path.isfile(os.path.join(src, name)):
                shutil.copy2(os.path.join(src, name), os.path.join(dst, name))

        # Postal-code dictionaries live in zipcode/ and use the same prefix.
        zip_src = os.path.join(src, "zipcode")
        if os.path.isdir(zip_src):
            for name in sorted(os.listdir(zip_src)):
                if name.startswith("SKK-JISYO.") and os.path.isfile(os.path.join(zip_src, name)):
                    shutil.copy2(os.path.join(zip_src, name), os.path.join(dst, name))

        # Provenance / licence documents.
        for name in ("ChangeLog", "README.md", "unicode-license.txt"):
            path = os.path.join(src, name)
            if os.path.isfile(path):
                shutil.copy2(path, os.path.join(dst, name))

        installed = sorted(f for f in os.listdir(dst) if f.startswith("SKK-JISYO."))
        self.output.info(f"Installed {len(installed)} dictionary files into {dst}")

    def package_info(self):
        # Data package: no libraries and no headers to link against, so
        # cpp_info.libs stays empty. What consumers actually need is the
        # location of the dictionary tree, which is published as a property.
        self.cpp_info.set_property("skkdic_datadir", self.datadir)
        self.output.info(f"SKK dictionaries installed under: <package_folder>/{self.datadir}")