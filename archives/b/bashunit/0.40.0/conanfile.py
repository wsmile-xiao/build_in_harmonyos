#!/usr/bin/env python3
"""Conan recipe — bashunit 0.40.0 (custom single-file Bash CLI)."""

import os
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class BashunitConan(ConanFile):
    name = "bashunit"
    version = "0.40.0"
    description = "A fast, modern testing framework for Bash"
    license = "MIT"
    homepage = "https://bashunit.com/"
    url = "https://github.com/TypedDevs/bashunit"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        download(
            self,
            url=source["url"],
            filename="bashunit",
            sha256=source["sha256"],
        )

    def build(self):
        apply_conandata_patches(self)
        self.run(f'bash -n "{os.path.join(self.source_folder, "bashunit")}"')

    def package(self):
        copy(
            self,
            "bashunit",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        executable = os.path.join(self.package_folder, "bin", "bashunit")
        os.chmod(
            executable,
            os.stat(executable).st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
