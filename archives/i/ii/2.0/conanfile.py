#!/usr/bin/env python3
"""Conan recipe for ii 2.0, the FIFO based IRC client."""

import os

from conan import ConanFile
from conan.tools.files import get, patch
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class IiConan(ConanFile):
    name = "ii"
    version = "2.0"
    description = "A minimalistic FIFO and filesystem based IRC client."
    license = "MIT"
    homepage = "https://tools.suckless.org/ii/"
    url = "https://git.suckless.org/ii"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        for patch_file in self.conan_data.get("patches", []):
            patch(self, patch_file=os.path.join(self.export_sources_folder, patch_file), strip=1)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("ii requires a POSIX target (Linux or OHOS)")
        self.run(f'make -C "{self.source_folder}" -j1', env="conanbuild")

    def package(self):
        self.run(
            f'make -C "{self.source_folder}" install PREFIX= '
            f'MANPREFIX=/share/man DOCPREFIX=/share/doc DESTDIR="{self.package_folder}"',
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
