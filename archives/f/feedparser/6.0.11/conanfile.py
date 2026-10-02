#!/usr/bin/env python3
"""Conan recipe for feedparser 6.0.11 — universal feed (RSS/Atom) parser.

Pure Python (feedparser/), single runtime dependency: sgmllib3k (PyPI
requires_dist: ['sgmllib3k']). HarmonyOS PC adaptation: copytree staging
(awscli WR-008 pattern); feedparser.parse() on a string is fully offline —
no network in the import or parse path. No source patch required.

R38 note: no console_scripts entry point, no bin/ payload — library only.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)


class FeedparserConan(ConanFile):
    name = "feedparser"
    version = "6.0.11"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/kurtmckee/feedparser"
    description = "Parse RSS and Atom feeds in Python (lastversion dependency)"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    requires = "sgmllib3k/1.0.0"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["feedparser"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "feedparser-stage")
        shutil.rmtree(staging, ignore_errors=True)
        src_pkg = os.path.join(self.source_folder, "feedparser")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"feedparser package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(staging, "feedparser"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def package(self):
        staging = os.path.join(self.build_folder, "feedparser-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            os.path.join(staging, "feedparser"),
            os.path.join(site, "feedparser"),
            ignore=shutil.ignore_patterns("__pycache__"))
        src_lic = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(src_lic):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy2(src_lic, os.path.join(lic_dir, "LICENSE"))

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
