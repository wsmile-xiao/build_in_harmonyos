#!/usr/bin/env python3
"""Conan recipe for apt-dater-host 1.0.1.

apt-dater-host is a host helper application for apt-dater, a terminal-based
remote package update manager. It implements the ADP (apt-dater protocol)
for host-side package management via SSH.

This is a shell-script-only package — no compilation is required.
The apk variant (#!/bin/sh) is installed as it is the most portable,
using only POSIX shell tools (awk, sed, grep, uname) available on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class AptdaterhostConan(ConanFile):
    name = "apt-dater-host"
    version = "1.0.1"
    description = "Host helper application for apt-dater remote package update manager (ADP protocol)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/DE-IBH/apt-dater-host"

    package_type = "application"

    # Script-only package: no compiler or build_type needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation step — apt-dater-host is a pure shell script.
        # Verify script syntax as a sanity check.
        script = os.path.join(self.source_folder, "apk", "apt-dater-host")
        self.run(f'sh -n "{script}"')

    def package(self):
        # Install the apk variant script (most portable, uses /bin/sh)
        copy(self, "apt-dater-host", src=os.path.join(self.source_folder, "apk"),
             dst=os.path.join(self.package_folder, "bin"))
        # Install sudoers config
        copy(self, "apt-dater-host-sudoers", src=os.path.join(self.source_folder, "apk"),
             dst=os.path.join(self.package_folder, "res", "sudoers.d"))
        # Install config file from dpkg variant (most complete config)
        copy(self, "apt-dater-host.conf", src=os.path.join(self.source_folder, "dpkg"),
             dst=os.path.join(self.package_folder, "res", "etc"))
        # Install man page
        copy(self, "apt-dater-host.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "res", "man", "man1"))
        # Install ADP protocol documentation
        copy(self, "*", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "res", "doc"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
