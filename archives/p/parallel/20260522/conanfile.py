#!/usr/bin/env python3
"""Conan recipe for GNU Parallel 20260522."""
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


class ParallelConan(ConanFile):
    name = "parallel"
    version = "20260522"
    description = "Shell tool for executing jobs in parallel"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/parallel/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"GNU Parallel supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("perl/5.42.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "parallel")
        for name in ("parallel", "sem", "sql"):
            copy(self, name, src=os.path.join(self.source_folder, "src"), dst=bin_dir)
            os.chmod(os.path.join(bin_dir, name), 0o755)
        copy(self, "*.1", src=os.path.join(self.source_folder, "src"), dst=man_dir)
        copy(self, "README", src=self.source_folder, dst=doc_dir)
        copy(
            self,
            "GPL-3.0-or-later.txt",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
