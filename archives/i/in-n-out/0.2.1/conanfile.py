#!/usr/bin/env python3
"""Conan recipe for the pure Python in-n-out 0.2.1 library."""

import hashlib
import os
import shutil

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


class InNOutConan(ConanFile):
    name = "in-n-out"
    version = "0.2.1"
    description = "Pluggable dependency injection and result processing"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pyapp-kit/in-n-out"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        archive = os.environ.get("IN_N_OUT_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("in-n-out source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], strip_root=True,
                extract_filter="data")
        apply_conandata_patches(self)

    def build(self):
        self.run("python3 -m compileall -q src/in_n_out", cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "src", "in_n_out")
        target = os.path.join(self.package_folder, "lib", "python", "in_n_out")
        copy(self, "*.py", src=source, dst=target, keep_path=False)
        copy(self, "py.typed", src=source, dst=target, keep_path=False)
        licenses = copy(self, "LICENSE*", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("in-n-out source license was not packaged")

        # Preserve the upstream dynamic version lookup in __init__.py.
        dist_info = os.path.join(self.package_folder, "lib", "python",
                                 "in_n_out-0.2.1.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        shutil.copyfile(os.path.join(self.source_folder, "PKG-INFO"),
                        os.path.join(dist_info, "METADATA"))
        dist_license = copy(
            self, "LICENSE*", src=self.source_folder,
            dst=os.path.join(dist_info, "licenses"), keep_path=False)
        if not dist_license:
            raise ConanException("in-n-out dist-info license was not packaged")
        with open(os.path.join(dist_info, "top_level.txt"), "w",
                  encoding="utf-8", newline="\n") as metadata_file:
            metadata_file.write("in_n_out\n")

    def package_id(self):
        # The package contains Python sources and has no native ABI.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
