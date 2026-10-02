#!/usr/bin/env python3
"""Conan recipe for the pure Python incremental 24.7.2 library."""

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


class IncrementalConan(ConanFile):
    name = "incremental"
    version = "24.7.2"
    description = "A small library that versions Python projects"
    license = "MIT"
    homepage = "https://github.com/twisted/incremental"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        archive = os.environ.get("INCREMENTAL_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("incremental source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], strip_root=True,
                extract_filter="data")
        apply_conandata_patches(self)

    def build(self):
        # Syntax-check all upstream Python modules, including integrations that
        # are outside this core-only Conan package scope.
        self.run("python3 -m compileall -q src/incremental",
                 cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "src", "incremental")
        target = os.path.join(self.package_folder, "lib", "python", "incremental")
        # This Conan package exposes the dependency-free version API only.
        # Upstream's CLI and Hatch plugin require optional/runtime packages.
        for name in ("__init__.py", "_version.py"):
            if not copy(self, name, src=source, dst=target, keep_path=False):
                raise ConanException(f"incremental core module is missing: {name}")
        copy(self, "py.typed", src=source, dst=target, keep_path=False)
        licenses = copy(self, "LICENSE*", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("incremental source license was not packaged")

    def package_id(self):
        # The distributed files are pure Python and have no native ABI.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
