#!/usr/bin/env python3
"""Conan recipe for decorator 5.3.1 — decorator of decorators (and more)
(pure-Python single-file library, PyPI source, zero dependencies).

Pure Python package (package_type python-require): build via `pip install`
into the conan package folder, consumers add site-packages to PYTHONPATH.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class DecoratorConan(ConanFile):
    name = "decorator"
    version = "5.3.1"
    description = "Better living through Python with decorators"
    license = "BSD-2-Clause"
    homepage = "https://github.com/micheles/decorator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        py = sys.executable
        staging = os.path.join(self.build_folder, "pip-stage")
        self.run(f'{py} -m pip install --no-deps --target "{staging}" .',
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
        if not os.path.isdir(os.path.join(site, "decorator")):
            raise ConanException(f"decorator package missing under {site}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.output.info(f"PYTHONPATH={site}")
