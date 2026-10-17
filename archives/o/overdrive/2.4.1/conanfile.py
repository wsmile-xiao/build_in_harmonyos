#!/usr/bin/env python3
"""Conan recipe for overdrive 2.4.1 — OverDrive (.odm) audiobook downloader.

Upstream: https://github.com/chbrown/overdrive (tag 2.4.1, 2025-05-21)
Build:    none. The release archive is exactly two files (README.md +
          overdrive.sh); the package installs the script as ``bin/overdrive``,
          the same action the Homebrew core formula performs
          (``bin.install "overdrive.sh" => "overdrive"``).

OHOS adaptation:
    No source patch is required. overdrive.sh:87 declares six runtime
    executables (curl, uuidgen, xmllint, iconv, openssl, base64); all of them
    resolve on the OHOS aarch64 PATH (/usr/bin toybox + /data/service/hnp/bin),
    and the script's own licence-hash pipeline (overdrive.sh:145) plus its XML
    metadata path (xmllint --xpath/--noblanks + sed + awk) are exercised with
    real data by test_package. The script needs a bash interpreter
    (``#!/usr/bin/env bash``); OHOS ships bash only in /data/service/hnp/bin,
    which is part of the device/CI system PATH and of the Conan profile
    buildenv, so the installed script is directly executable.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rename)
from conan.tools.layout import basic_layout


class OverdriveConan(ConanFile):
    name = "overdrive"
    version = "2.4.1"
    description = ("Download the DRM-free MP3 parts of an audiobook loan from "
                   "an OverDrive .odm file (single-file Bash CLI)")
    license = "MIT"
    homepage = "https://github.com/chbrown/overdrive"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audiobook", "overdrive", "odm", "cli", "bash")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"overdrive supports Linux/OHOS only, got {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        # No patch is needed on OHOS (see module docstring); the hook is kept so
        # that conandata.yml `patches:` stays the single point of truth.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Nothing to compile; keep the executable bit so package() can copy it
        # straight into bin/ (HMDFS may normalise modes, hence the explicit chmod).
        script = os.path.join(self.source_folder, "overdrive.sh")
        if os.path.isfile(script):
            os.chmod(script, 0o755)

    def package_id(self):
        # Architecture-independent Bash script: one package for every build.
        self.info.clear()

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "overdrive.sh", src=self.source_folder, dst=bindir,
             keep_path=False)
        installed = os.path.join(bindir, "overdrive.sh")
        rename(self, installed, os.path.join(bindir, "overdrive"))
        script = os.path.join(bindir, "overdrive")
        if os.path.isfile(script):
            os.chmod(script, 0o755)
        # Upstream ships no LICENSE file; README.md (which carries the MIT
        # notice, README.md:263-266) is installed as documentation.
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "overdrive"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
