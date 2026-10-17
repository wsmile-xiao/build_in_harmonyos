#!/usr/bin/env python3
"""Conan recipe for pyfavicon 0.1.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PyfaviconConan(ConanFile):
    name = "pyfavicon"
    version = "0.1.1"
    description = "Async favicon fetcher"
    license = "MIT"
    homepage = "https://github.com/bilelmoussaoui/pyfavicon"
    url = "https://pypi.org/project/pyfavicon/0.1.1/"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pyfavicon supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        package_site = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
            "pyfavicon",
        )
        copy(
            self,
            "*.py",
            src=os.path.join(self.source_folder, "pyfavicon"),
            dst=package_site,
            keep_path=True,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "pyfavicon"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
