#!/usr/bin/env python3
"""Conan recipe for raku-log 0.3.1 — pure Raku 6.d module distribution.

The upstream release ships Raku module sources only; there is no native
compilation step. The package is consumed at runtime by the published
OHOS Rakudo (MoarVM) toolchain, which is declared as a run requirement.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RakuLogConan(ConanFile):
    name = "raku-log"
    version = "0.3.1"
    description = "A standard logging interface for Raku applications"
    license = "LGPL-3.0-only"
    homepage = "https://git.tyil.nl/raku/log"
    url = "https://git.tyil.nl/raku/log"
    # Nothing is compiled here, but the OHOS CI profile and the L0 quality gate
    # require the full settings tuple, so all four are declared even though only
    # os/arch actually describe this source-only artifact.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("rakudo/2025.11", run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("raku-log supports Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration("raku-log supports armv8 and x86_64")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.rakumod", src=self.source_folder, dst=self.package_folder, excludes=".precomp/**")
        copy(self, "META6.json", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "RAKULIB", f"{self.package_folder}/lib"
        )
