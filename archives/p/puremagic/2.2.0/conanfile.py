#!/usr/bin/env python3
"""Conan recipe for the pure Python puremagic file signature library."""

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


class PuremagicConan(ConanFile):
    name = "puremagic"
    version = "2.2.0"
    description = "Pure Python implementation of file type detection"
    license = "MIT"
    homepage = "https://github.com/cdgriffith/puremagic"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # Keep any future conandata patches in the exported recipe sources.
        export_conandata_patches(self)

    def source(self):
        archive = os.environ.get("PUREMAGIC_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("puremagic source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], extract_filter="data")
        # The current patch list is empty; keep the standard Conan hook so
        # conandata patches are applied if this recipe later declares them.
        apply_conandata_patches(self)

    def build(self):
        # The package is pure Python; compile the distributed sources with the
        # target interpreter to catch syntax errors before packaging.
        self.run("python3 -m compileall -q puremagic", cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "puremagic")
        target = os.path.join(self.package_folder, "lib", "python", "puremagic")
        copied = copy(self, "*.py", src=source, dst=target, keep_path=True)
        if not copied:
            raise ConanException("puremagic Python sources were not packaged")
        data = copy(self, "*.json", src=source, dst=target, keep_path=True)
        if not data:
            raise ConanException("puremagic signature database was not packaged")
        licenses = copy(self, "LICENSE*", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("puremagic MIT license was not packaged")

    def package_id(self):
        # The package has no native ABI or runtime dependencies.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
