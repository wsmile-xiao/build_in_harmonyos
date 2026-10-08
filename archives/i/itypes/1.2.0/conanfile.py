#!/usr/bin/env python3
"""Conan recipe for the pure Python itypes 1.2.0 module."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ITypesConan(ConanFile):
    name = "itypes"
    version = "1.2.0"
    description = "Simple immutable container types for Python"
    license = "BSD-3-Clause"
    homepage = "https://github.com/PavanTatikonda/itypes"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        copy(self, "LICENSE.md", src=self.recipe_folder,
             dst=self.export_sources_folder, keep_path=False)
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The current recipe has no patches; keep conandata patches active if added.
        apply_conandata_patches(self)

    def build(self):
        self.run("python3 -m compileall -q itypes.py", cwd=self.source_folder)

    def package(self):
        copied = copy(self, "itypes.py", src=self.source_folder,
                      dst=os.path.join(self.package_folder, "lib", "python"),
                      keep_path=False)
        if not copied:
            raise RuntimeError("itypes.py was not packaged")
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
