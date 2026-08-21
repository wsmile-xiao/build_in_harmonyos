#!/usr/bin/env python3
"""Conan recipe for toml 0.10.2 — Python Library for TOML
(pure-Python, PyPI source, zero dependencies).

Pure Python package (package_type python-require): build via `pip install`
into the conan package folder, consumers add site-packages to PYTHONPATH.
Runtime dependency of confspirator (example.py top-level `import toml`).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class TomlConan(ConanFile):
    name = "toml"
    version = "0.10.2.1"
    description = "Python Library for Tom's Obvious, Minimal Language"
    license = "MIT"
    homepage = "https://github.com/uiri/toml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "python-require"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Pure Python package (single toml/ dir): copy the source tree
        # instead of `pip install`. pip's egg_info hits a broken pbr
        # entry point on this host (ModuleNotFoundError: No module named
        # 'pbr') — copying is deterministic and needs no setuptools
        # (same fix as PR #5776).
        install_target = os.path.join(self.build_folder, "install")
        shutil.copytree(os.path.join(self.source_folder, "toml"),
                        os.path.join(install_target, "toml"))

    def package(self):
        staging = os.path.join(self.build_folder, "install")
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
        if not os.path.isdir(os.path.join(site, "toml")):
            raise ConanException(f"toml package missing under {site}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.output.info(f"PYTHONPATH={site}")
