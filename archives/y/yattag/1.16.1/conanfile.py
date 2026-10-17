#!/usr/bin/env python3
"""Conan recipe for the pure Python yattag 1.16.1 library."""

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


class YattagConan(ConanFile):
    name = "yattag"
    version = "1.16.1"
    description = "Generate HTML or XML documents in a pythonic way"
    license = "LGPL-2.1-only"
    homepage = "https://www.yattag.org"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        archive = os.environ.get("YATTAG_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != source["sha256"]:
                raise ConanException("yattag source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **source, strip_root=True, extract_filter="data")

    def build(self):
        apply_conandata_patches(self)
        self.run("python3 -m compileall -q yattag", cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "yattag")
        target = os.path.join(self.package_folder, "lib", "python", "yattag")
        copied = copy(self, "*.py", src=source, dst=target,
                      excludes=["test/*"])
        if not copied:
            raise ConanException("yattag Python modules were not packaged")
        copy(self, "py.typed", src=source, dst=target, keep_path=False)

        license_source = os.path.join(self.source_folder, "license")
        licenses = copy(self, "*", src=license_source,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("yattag license files were not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
