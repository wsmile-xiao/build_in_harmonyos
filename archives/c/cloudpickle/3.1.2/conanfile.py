#!/usr/bin/env python3
"""Conan recipe for cloudpickle 3.1.2 — pure Python library.

cloudpickle serializes Python constructs not supported by the default
pickle module. It is a base (non-optional) dependency of Gymnasium.
Pure Python: package copies the cloudpickle package into site-packages.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CloudpickleConan(ConanFile):
    name = "cloudpickle"
    version = "3.1.2"
    description = "Extended pickling support for Python objects"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cloudpipe/cloudpickle"
    url = ""

    package_type = "python-require"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "cloudpickle")):
            raise ConanException("cloudpickle/ package dir not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(pkg_dir, exist_ok=True)
        shutil.copytree(
            os.path.join(self.source_folder, "cloudpickle"),
            os.path.join(pkg_dir, "cloudpickle"),
            dirs_exist_ok=True,
        )
        # Also copy py.typed / LICENSE if present
        for f in ("LICENSE", "LICENSE.md", "py.typed"):
            src = os.path.join(self.source_folder, f)
            if os.path.isfile(src):
                shutil.copy2(src, pkg_dir)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []