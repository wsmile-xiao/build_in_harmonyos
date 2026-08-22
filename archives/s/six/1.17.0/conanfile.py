#!/usr/bin/env python3
"""Conan recipe for the pure-Python six compatibility module."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SixConan(ConanFile):
    name = "six"
    version = "1.17.0"
    description = "Python 2 and 3 compatibility utilities"
    license = "MIT"
    homepage = "https://github.com/benjaminp/six"
    url = "https://github.com/benjaminp/six"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"six 1.17.0 supports Linux and OHOS only, got {self.settings.os}"
            )

    def package_id(self):
        # six.py is architecture independent.
        self.info.clear()

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def build(self):
        module = Path(self.source_folder) / "six.py"
        source = module.read_text(encoding="utf-8")
        compile(source, str(module), "exec")

        version_line = '__version__ = "1.17.0"'
        if version_line not in source:
            raise ConanException("six.py does not declare the expected version")

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        copy(
            self,
            "six.py",
            src=self.source_folder,
            dst=site_packages,
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("SIX_PACKAGE_ROOT", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
