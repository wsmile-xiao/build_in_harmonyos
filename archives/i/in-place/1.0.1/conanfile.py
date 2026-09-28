"""Conan recipe for the pure-Python in-place package."""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout


class InPlaceConan(ConanFile):
    name = "in-place"
    version = "1.0.1"
    description = "In-place file processing for Python"
    license = "MIT"
    homepage = "https://github.com/jwodder/inplace"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        archive = os.environ.get("IN_PLACE_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("in-place source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], strip_root=True,
                extract_filter="data")
        apply_conandata_patches(self)

    def build(self):
        self.run("python3 -m compileall -q src/in_place",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "*.py", src=os.path.join(self.source_folder, "src", "in_place"),
             dst=os.path.join(self.package_folder, "python", "in_place"))
        copy(self, "py.typed", src=os.path.join(self.source_folder, "src", "in_place"),
             dst=os.path.join(self.package_folder, "python", "in_place"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "python")
        )
