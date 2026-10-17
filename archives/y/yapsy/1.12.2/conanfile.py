"""Conan recipe for the pure-Python Yapsy plugin manager."""

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


class YapsyConan(ConanFile):
    name = "yapsy"
    version = "1.12.2"
    description = "Yet another plugin system for Python"
    license = "BSD-2-Clause AND ISC"
    homepage = "https://pypi.org/project/Yapsy/1.12.2/"
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
        apply_conandata_patches(self)

    def build(self):
        """Yapsy is pure Python and has no native build step."""
        pass

    def package(self):
        python_package = os.path.join(self.source_folder, "yapsy")
        python_destination = os.path.join(
            self.package_folder, "lib", "python", "yapsy")
        if not copy(self, "*.py", src=python_package, dst=python_destination,
                    keep_path=False):
            raise ConanException("Yapsy Python modules are missing")

        license_destination = os.path.join(
            self.package_folder, "share", "licenses", "yapsy")
        if not copy(self, "LICENSE.txt", src=self.source_folder,
                    dst=license_destination, keep_path=False):
            raise ConanException("Yapsy license file is missing")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
