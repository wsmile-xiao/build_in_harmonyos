#!/usr/bin/env python3
"""Conan recipe for the pure-Python jdcal 1.4.1 module."""

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


class JdcalConan(ConanFile):
    name = "jdcal"
    version = "1.4.1"
    description = "Julian dates from proleptic Gregorian and Julian calendars"
    license = "BSD-2-Clause"
    homepage = "https://github.com/phn/jdcal"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        # Declared patches, if any, travel with the recipe; an empty list is valid.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        archive = os.environ.get("JDCAL_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("jdcal source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], strip_root=True,
                extract_filter="data")

    def build(self):
        apply_conandata_patches(self)
        self.run("python3 -m compileall -q jdcal.py", cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "jdcal.py")
        target = os.path.join(self.package_folder, "lib", "python")
        if not os.path.isfile(source):
            raise ConanException("jdcal.py was not found in the fixed source")
        copy(self, "jdcal.py", src=self.source_folder, dst=target,
             keep_path=False)
        licenses = copy(self, "LICENSE.txt", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("jdcal license was not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
