#!/usr/bin/env python3
"""Conan recipe for typing-extensions 4.16.0 — pure Python library (setuptools).

HarmonyOS PC adaptation: Python package with src/ layout,
copies the typing_extensions module into site-packages for import.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TypingExtensionsConan(ConanFile):
    name = "typing-extensions"
    version = "4.16.0"
    description = "Backported and Experimental Type Hints for Python"
    license = "PSF-2.0"
    homepage = "https://github.com/python/typing_extensions"
    url = "https://github.com/python/typing_extensions"

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
        if not os.path.isfile(os.path.join(self.source_folder, "src", "typing_extensions.py")):
            raise ConanException("typing_extensions.py not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(pkg_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "src", "typing_extensions.py"),
            os.path.join(pkg_dir, "typing_extensions.py"),
        )

    def package_info(self):
        self.cpp_info.libs = []