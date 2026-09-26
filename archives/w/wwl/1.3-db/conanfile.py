#!/usr/bin/env python3
"""Conan recipe for wwl 1.3-db - Maidenhead locator utility.

``wwl`` computes distance (QRB) and azimuth between two Maidenhead locators;
when invoked as ``locator`` it converts one locator to latitude/longitude.
It is a single C file built by a hand-written Makefile and links only libm.

Source note
-----------
Upstream publishes the tarball only over plain HTTP
(``http://www.db.net/downloads/wwl+db-1.3.tgz``), which the repository rules
forbid in ``conandata.yml``.  This recipe therefore uses Debian's verbatim
``.orig.tar.gz`` (same upstream release, served over HTTPS) with a pinned
SHA-256.

No upstream test suite exists (the Makefile has only ``all``/``install``/
``release``/``clean``), so the recipe relies on the consumer assertions in
``test_package/``.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class WwlConan(ConanFile):
    name = "wwl"
    version = "1.3-db"
    description = "Maidenhead locator utility: distance/azimuth (wwl) and locator->lat/lon (locator)"
    license = "LicenseRef-Permissive"
    homepage = "https://www.db.net/downloads/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "wwl OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        # Hand-written Makefile: builds `wwl` (links -lm) then the `locator`
        # symlink. -j1 per repository rule R9.
        self.run('make CC="{}" CFLAGS="-Wall -O2" -j1'.format(cc),
                 cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "wwl")):
            raise ConanInvalidConfiguration("build did not produce the 'wwl' program")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man1_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "wwl", self.source_folder, bin_dir)
        copy(self, "wwl.1", self.source_folder, man1_dir)
        # The program selects its mode from argv[0]'s basename, so ship a real
        # second executable (and man page) named `locator` rather than relying
        # on a symlink surviving packaging.
        shutil.copyfile(os.path.join(bin_dir, "wwl"), os.path.join(bin_dir, "locator"))
        os.chmod(os.path.join(bin_dir, "locator"), 0o755)
        shutil.copyfile(os.path.join(man1_dir, "wwl.1"), os.path.join(man1_dir, "locator.1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
