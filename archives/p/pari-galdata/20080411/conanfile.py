#!/usr/bin/env python3
"""Conan recipe for pari-galdata 20080411 — the PARI/GP Galois group
data package.

This is a **pure data package**: the upstream tarball ships a
``data/galdata/`` directory with 344 data files — 4 human-readable group
name tables (``NAM8`` .. ``NAM11``, degrees 8..11) and 340 binary tables
(197 ``COS<p>_<n>_<k>`` coset-action files and 143 ``RES<...>``
resolvent files) used by ``polgalois`` for degrees 8 through 11.
There is nothing to compile, link or sign — packaging is "unpack tarball
and install the data files", so the recipe is architecture-independent
(``package_id`` is cleared) and ``build()`` only runs the deterministic
data validator that is also used by ``test_package``.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class PariGaldataConan(ConanFile):
    name = "pari-galdata"
    version = "20080411"
    description = (
        "Galois group data for PARI/GP: group name tables and "
        "coset/resolvent data for polgalois, degrees 8 to 11"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/"
    url = "https://pari.math.u-bordeaux.fr/pub/pari/packages/galdata.tgz"
    package_type = "unknown"

    # Pure data package: no compiler touches any artifact.  The full
    # settings tuple is declared (L0p requires all four for the OHOS
    # profile), but package_id() below clears the recipe, so every
    # platform shares the same noarch package.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(
            self,
            "test_pari_galdata.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )
        copy(
            self,
            "hashes_galdata.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")
        self.settings.rm_safe("compiler.cppstd")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename="galdata-20080411.tgz",
            strip_root=False,
        )
        apply_conandata_patches(self)

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "test_pari_galdata.py",
        )

    def build(self):
        # Deterministic data validation on the unpacked source tree, run
        # during create() so a corrupt download fails the build (R34: a
        # data package has no callable API, integrity checking replaces
        # the compile smoke test).
        command = (
            f'"{sys.executable}" "{self._validator}" '
            f'--source-root "{self.source_folder}"'
        )
        self.run(command)

    def package(self):
        data_dir = os.path.join(
            self.package_folder, "share", "pari", "galdata"
        )

        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "data", "galdata"),
            dst=data_dir,
            keep_path=False,
        )
        # The galdata tarball carries neither COPYING nor README; the
        # package is GPL-2.0-or-later as part of PARI/GP (stated on the
        # upstream packages page).  Record the license reference here.
        licenses_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(licenses_dir, exist_ok=True)
        with open(
            os.path.join(licenses_dir, "COPYING"),
            "w",
            encoding="utf-8",
        ) as fh:
            fh.write(
                "pari-galdata is part of the PARI/GP data packages and is\n"
                "distributed under the GNU General Public License,\n"
                "version 2 or later (GPL-2.0-or-later), as is PARI/GP\n"
                "itself.  See https://pari.math.u-bordeaux.fr/ and the\n"
                "PARI/GP COPYING file for the full license text.\n"
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]

        data_dir = os.path.join(
            self.package_folder, "share", "pari", "galdata"
        )
        self.buildenv_info.define_path("PARI_GALDATA_DIR", data_dir)
        self.runenv_info.define_path("PARI_GALDATA_DIR", data_dir)
        self.conf_info.define(
            "user.pari-galdata:data_dir", data_dir
        )
