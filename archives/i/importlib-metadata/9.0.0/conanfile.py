#!/usr/bin/env python3
"""Conan recipe for importlib-metadata 9.0.0 — pure-Python backport of
importlib.metadata (reads package metadata / entry points, PyPI source).

Pure Python (zero compilation) — pip install --no-deps --target staging,
site-packages copied into the package. Only runtime dep zipp is published
on ohpcd (4.1.0).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class ImportlibMetadataConan(ConanFile):
    name = "importlib-metadata"
    version = "9.0.0"
    description = "Library to access the metadata for a Python package"
    license = "Apache-2.0"
    homepage = "https://github.com/python/importlib_metadata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # only runtime dep (PyPI requires_dist verified, published on ohpcd)
        self.requires("zipp/4.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        py = sys.executable
        staging = os.path.join(self.build_folder, "pip-stage")
        self.run(
            f'{py} -m pip install --no-deps --target "{staging}" .',
            cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "pip-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"pip staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        for entry in os.listdir(staging):
            src = os.path.join(staging, entry)
            dst = os.path.join(site, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        if not os.path.isdir(os.path.join(site, "importlib_metadata")):
            raise ConanException(
                "importlib_metadata package missing under {site}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.output.info(f"PYTHONPATH={site}")
