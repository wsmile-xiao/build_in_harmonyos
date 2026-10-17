#!/usr/bin/env python3
"""Conan recipe for binwalk 2.3.4 — Python firmware analysis tool (setuptools)."""
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class BinwalkConan(ConanFile):
    name = "binwalk"
    version = "2.3.4"
    description = "Firmware analysis tool for searching binary images for embedded files and code"
    license = "MIT"
    homepage = "https://github.com/ReFirmLabs/binwalk"
    url = "https://github.com/ReFirmLabs/binwalk"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pydeps(self):
        # Private build-folder prefix for setuptools (R49: never inject into
        # shared interpreter site-packages).
        return os.path.join(self.build_folder, "pydeps")

    def build(self):
        apply_conandata_patches(self)
        # The HarmonyOS PC system Python ships without setuptools; install it
        # into the private build prefix and expose it via PYTHONPATH.
        pydeps = self._pydeps()
        self.run(f'python3 -m pip install --no-deps --quiet --target "{pydeps}" setuptools 2>&1',
                 cwd=self.source_folder)
        self.run(f'PYTHONPATH="{pydeps}" python3 setup.py build', cwd=self.source_folder)

    def package(self):
        pydeps = self._pydeps()
        self.run(f'PYTHONPATH="{pydeps}" python3 setup.py install --no-compile '
                 f'--prefix="{self.package_folder}"', cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Locate lib/pythonX.Y/site-packages created by setup.py install
        # without hard-coding the interpreter version.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for entry in os.listdir(libdir):
                site = os.path.join(libdir, entry, "site-packages")
                if entry.startswith("python") and os.path.isdir(site):
                    self.runenv_info.append_path("PYTHONPATH", site)
                    break
