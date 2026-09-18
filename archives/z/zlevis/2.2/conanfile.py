#!/usr/bin/env python3
"""Conan recipe for zlevis 2.2 — pure POSIX shell tool.

zlevis is a minimal fork of Clevis, rewritten in POSIX shell, that enables
automatic decryption of ZFS root pools with TPM2. Upstream ships three shell
scripts (zlevis / zlevis-encrypt / zlevis-decrypt) installed via Meson's
install_data. There is no compiled code, so the recipe simply stages the
scripts into bin/ (same pattern as the acme.sh pure-shell recipe).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ZlevisConan(ConanFile):
    name = "zlevis"
    version = "2.2"
    description = "Tool that enables automatic decryption of ZFS root pools with TPM2"
    license = "GPL-3.0-only"
    homepage = "https://git.ampel.dev/ampel/zlevis"
    url = "https://git.ampel.dev/ampel/zlevis"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for script in ("zlevis", "zlevis-encrypt", "zlevis-decrypt"):
            src = os.path.join(self.source_folder, "src", script)
            copy(self, script, src=os.path.join(self.source_folder, "src"),
                 dst=bindir, keep_path=False)
            os.chmod(os.path.join(bindir, script), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []