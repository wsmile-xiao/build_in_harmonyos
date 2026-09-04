#!/usr/bin/env python3
"""Conan recipe for rdflib 7.1.4 and its runtime Python dependencies."""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class RdflibConan(ConanFile):
    name = "python3-rdflib"
    version = "7.1.4"
    description = "RDF library for Python 3"
    license = "BSD-3-Clause"
    homepage = "https://github.com/RDFLib/rdflib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self._site = os.path.join(self.build_folder, "staging", "lib", pyver, "site-packages")
        os.makedirs(self._site, exist_ok=True)
        source_pkg = os.path.join(self.source_folder, "rdflib")
        if not os.path.isdir(source_pkg):
            raise ConanException("rdflib source package directory is missing")
        shutil.copytree(source_pkg, os.path.join(self._site, "rdflib"))
        dist_info = os.path.join(self._site, "rdflib-7.1.4.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write("Metadata-Version: 2.1\nName: rdflib\nVersion: 7.1.4\n")
        with open(os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8") as handle:
            handle.write("rdflib\n")

        # Keep the configure-time import self-contained and deterministic.
        self.run(
            f"{sys.executable} -m pip install --no-cache-dir --target "
            f'"{self._site}" isodate==0.7.2 pyparsing==3.2.3'
        )

    def package(self):
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        staging = os.path.join(self.build_folder, "staging", "lib", pyver, "site-packages")
        if not os.path.isdir(staging):
            raise ConanException("rdflib staging directory is missing")
        copy(self, "*", src=staging, dst=site)

    def package_info(self):
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
