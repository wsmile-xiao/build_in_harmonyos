#!/usr/bin/env python3
"""Conan recipe for the pure-Python parso 0.8.7 package."""

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


class ParsoConan(ConanFile):
    name = "parso"
    version = "0.8.7"
    description = "A Python parser with error recovery and round-trip parsing"
    license = "MIT"
    homepage = "https://github.com/davidhalter/parso"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        archive = os.environ.get("PARSO_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("parso source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], strip_root=True,
                extract_filter="data")
        apply_conandata_patches(self)

    def build(self):
        self.run("python3 -m compileall -q parso", cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "parso")
        package_root = os.path.join(self.package_folder, "lib", "python", "parso")
        python_source = os.path.join(source, "python")
        modules = copy(self, "*.py", src=source, dst=package_root,
                       keep_path=True, excludes=["__pycache__/*"])
        stubs = copy(self, "*.pyi", src=source, dst=package_root,
                     keep_path=True, excludes=["__pycache__/*"])
        grammars = copy(self, "grammar*.txt", src=python_source,
                        dst=os.path.join(package_root, "python"),
                        keep_path=False)
        typed_marker = copy(self, "py.typed", src=source, dst=package_root,
                            keep_path=False)
        if not modules or not grammars or not typed_marker:
            raise ConanException("parso modules, grammar data, or typing marker missing")

        licenses = copy(self, "LICENSE.txt", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("parso license was not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
