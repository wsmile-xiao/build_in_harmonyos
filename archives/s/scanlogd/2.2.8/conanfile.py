#!/usr/bin/env python3
"""Conan recipe for scanlogd 2.2.8 on HarmonyOS PC (aarch64).

scanlogd is a daemon that detects and logs TCP port scans.  This recipe uses
upstream's Linux raw-socket capture backend, which has no libpcap dependency.
The packet-processing logic in scanlogd.c is not modified.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ScanlogdConan(ConanFile):
    name = "scanlogd"
    version = "2.2.8"
    description = "TCP port scan detection daemon"
    license = "LicenseRef-Openwall-BSD-cut-down"
    homepage = "https://www.openwall.com/scanlogd/"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"scanlogd supports Linux/OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The upstream default target intentionally does not build a binary.
        # Select the Linux raw-socket backend to avoid an undeclared libpcap
        # dependency and preserve the upstream capture implementation.
        self.run(
            "make CC=clang linux -j1",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "scanlogd",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "scanlogd.8",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man8"),
            keep_path=False,
        )
        copy(
            self,
            "scanlogd.init",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "etc"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "scanlogd"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        bin_path = os.path.join(self.package_folder, "bin", "scanlogd")
        if not os.path.isfile(bin_path):
            raise ConanException("scanlogd build did not produce a binary")
        os.chmod(bin_path, 0o755)
        self._sign_ohos_binary(bin_path)

    def _sign_ohos_binary(self, bin_path):
        if self.settings.os != "OHOS":
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool) or not os.path.isfile(objcopy):
            raise ConanException(
                "OHOS ELF signing tools are unavailable; refusing to package "
                "an unsigned executable"
            )

        # A freshly linked executable normally has no .codesign section.
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", bin_path],
            capture_output=True,
            check=False,
            timeout=10,
        )

        signed_path = bin_path + ".signed"
        result = subprocess.run(
            [
                sign_tool,
                "sign",
                "-inFile",
                bin_path,
                "-outFile",
                signed_path,
                "-selfSign",
                "1",
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0 or not os.path.isfile(signed_path):
            raise ConanException(
                f"OHOS ELF signing failed for scanlogd (rc={result.returncode})"
            )
        os.replace(signed_path, bin_path)
        os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["etc", "share"]
