#!/usr/bin/env python3
"""Conan recipe for platformdirs 4.3.8, a pure-Python directory helper."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PlatformdirsConan(ConanFile):
    name = "platformdirs"
    version = "4.3.8"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/tox-dev/platformdirs"
    description = "Determine appropriate platform-specific directories for applications."
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "src", "platformdirs")):
            raise ConanException("platformdirs source package is missing")

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def package(self):
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(site, exist_ok=True)
        source_package = os.path.join(self.source_folder, "src", "platformdirs")
        if not os.path.isdir(source_package):
            raise ConanException(f"platformdirs package missing: {source_package}")
        shutil.copytree(source_package, os.path.join(site, "platformdirs"))

    def package_info(self):
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib", "python3.12", "site-packages"))
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib", "python3.12", "site-packages"))
