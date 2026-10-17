#!/usr/bin/env python3
"""Conan recipe for Mycroft Adapt Intent Parser 1.0.0.

Adapt is a pure-Python intent parser.  The recipe stages the importable modules
directly; the runtime dependency ``six`` must be supplied independently.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AdaptConan(ConanFile):
    name = "adapt"
    version = "1.0.0"
    description = "Flexible and extensible natural-language intent parser"
    license = "Apache-2.0"
    homepage = "https://github.com/MycroftAI/adapt"
    url = "https://github.com/MycroftAI/adapt"
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"adapt 1.0.0 supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        # Adapt is pure Python and setup.py only supplies setuptools metadata.
        # Copy the importable package directly so this recipe does not need a
        # host setuptools installation or perform network package resolution.
        copy(self, "*.py", src=os.path.join(self.source_folder, "adapt"),
             dst=os.path.join(staging, "adapt"), keep_path=True)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=staging,
             dst=os.path.join(self.package_folder, "lib", "python", "site-packages"),
             keep_path=True)
        for license_name in ("LICENSE.md", "LICENSE", "LICENCE"):
            license_path = os.path.join(self.source_folder, license_name)
            if os.path.isfile(license_path):
                copy(
                    self,
                    license_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False,
                )
                break

    def package_info(self):
        # This is a Python package; consumers import it through PYTHONPATH.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        site_packages = os.path.join(self.package_folder, "lib", "python", "site-packages")
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
