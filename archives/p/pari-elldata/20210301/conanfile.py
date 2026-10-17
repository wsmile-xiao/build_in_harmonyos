#!/usr/bin/env python3
"""Conan recipe for pari-elldata 20210301 — the PARI/GP elliptic curve data
package (J. E. Cremona's database).

This is a **pure data package**: the upstream tarball ships a
``data/elldata/`` directory with 500 data files (``ell0`` .. ``ell499``,
one file per 1000-conductor range) plus a README.  There is nothing to
compile, link or sign — packaging is "unpack tarball and install the data
files", so the recipe is architecture-independent (``package_id`` is
cleared) and ``build()`` only runs the deterministic data validator that
is also used by ``test_package``.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class PariElldataConan(ConanFile):
    name = "pari-elldata"
    version = "20210301"
    description = (
        "J. E. Cremona's elliptic curve database for PARI/GP "
        "(ellsearch / ellidentify / ellgenerators data)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/"
    url = "https://pari.math.u-bordeaux.fr/pub/pari/packages/elldata.tgz"
    package_type = "unknown"

    # Pure data package: no compiler touches any artifact.  The full
    # settings tuple is declared (L0p requires all four for the OHOS
    # profile), but package_id() clears the recipe below, so every
    # platform shares the same noarch package.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(
            self,
            "test_pari_elldata.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )
        copy(
            self,
            "hashes_elldata.py",
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
            filename="elldata-20210301.tgz",
            strip_root=False,
        )
        apply_conandata_patches(self)

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "test_pari_elldata.py",
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
            self.package_folder, "share", "pari", "elldata"
        )
        docs_dir = os.path.join(
            self.package_folder, "share", "doc", "pari-elldata"
        )

        copy(
            self,
            "ell*",
            src=os.path.join(self.source_folder, "data", "elldata"),
            dst=data_dir,
            keep_path=False,
        )
        copy(
            self,
            "README",
            src=os.path.join(self.source_folder, "data", "elldata"),
            dst=docs_dir,
            keep_path=False,
        )
        # The tarball carries no COPYING file; the README states the
        # package is GPL-2.0-or-later (same as PARI/GP itself).  Package
        # the README as the license reference.
        copy(
            self,
            "README",
            src=os.path.join(self.source_folder, "data", "elldata"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
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
            self.package_folder, "share", "pari", "elldata"
        )
        self.buildenv_info.define_path("PARI_ELLDATA_DIR", data_dir)
        self.runenv_info.define_path("PARI_ELLDATA_DIR", data_dir)
        self.conf_info.define(
            "user.pari-elldata:data_dir", data_dir
        )
