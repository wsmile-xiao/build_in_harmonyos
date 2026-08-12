#!/usr/bin/env python3
"""Conan recipe for propcache 0.5.2 — Python library (setuptools + optional C extension).

HarmonyOS PC adaptation: packages the pure-Python fallback of propcache
(the _helpers_c C extension is optional; __init__.py degrades to _helpers_py).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PropcacheConan(ConanFile):
    name = "propcache"
    version = "0.5.2"
    description = "Accelerated property cache"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/propcache"
    url = "https://github.com/aio-libs/propcache"

    package_type = "python-require"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # src/ layout: package lives in src/propcache after strip_root
        src_pkg = os.path.join(self.source_folder, "src", "propcache")
        if not os.path.isdir(src_pkg):
            raise ConanException("propcache package directory not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "propcache")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "propcache")
        for f in os.listdir(src):
            if f.endswith(".pyx"):
                continue  # Cython source not needed; pure-Python fallback used
            shutil.copy2(os.path.join(src, f), os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []