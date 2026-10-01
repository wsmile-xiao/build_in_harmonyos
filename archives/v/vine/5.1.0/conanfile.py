#!/usr/bin/env python3
"""Conan recipe for the pure Python Vine promise library."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class VineConan(ConanFile):
    name = "vine"
    version = "5.1.0"
    description = "Python promises and synchronization primitives"
    license = "BSD-3-Clause"
    homepage = "https://github.com/celery/vine"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The source patch only adapts the upstream pytest fixture hook.
        apply_conandata_patches(self)

    def build(self):
        self.output.info("Pure Python package; no native build step")

    def package(self):
        source = os.path.join(self.source_folder, "vine")
        target = os.path.join(self.package_folder, "lib", "python", "vine")
        copied = copy(self, "*.py", src=source, dst=target, keep_path=False)
        if not copied:
            raise ConanException("Vine Python modules were not packaged")
        if not copy(self, "LICENSE", src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False):
            raise ConanException("Vine LICENSE was not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
