#!/usr/bin/env python3
"""Conan recipe — kerberos-configs 2.7 (Debian kerberos configuration files).

Pure configuration package: upstream ships the krb5.conf template plus the
Debian debconf integration scripts. There is no compile toolchain at all
(debian/rules only assembles a debconf config script via cat/genblob for the
Debian installer; conandata payload is the config template itself).

Adapted for HarmonyOS PC (arm64) as a packaging-only recipe: the krb5.conf
template, docs and the realm-parsing perl module are installed verbatim under
share/kerberos-configs/ (FHS layout matching
debian/krb5-config.install: "krb5.conf.template usr/share/kerberos-configs").

License: GPL-2.0-only (debian/copyright: "only version 2 of the License is
permitted").
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class KerberosConfigsConan(ConanFile):
    name = "kerberos-configs"
    version = "2.7"
    description = (
        "Configuration files for Kerberos Version 5 (Debian krb5-config: "
        "krb5.conf template + realm parsing helper)"
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/deepin-community/kerberos-configs"
    url = "https://github.com/deepin-community/kerberos-configs"

    package_type = "library"  # noarch data/config package
    # L0p: all four settings required by the OHOS profile gate; the actual
    # package payload is configuration data (arch-independent).
    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def package_id(self):
        # noarch: the payload is pure config data — identical for every
        # os/compiler/build_type/arch combination (adamstark-audiofile 1.1.4
        # precedent). Clears settings/options from the package id.
        self.info.clear()

    def validate(self):
        # R32: os check must accept both Linux and OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # G1 gate: export_sources() must be declared; no patches needed
        pass

    def source(self):
        # codeload URLs end in the tag name (".../tar.gz/refs/tags/2.7")
        # which has no file extension, so Conan's get() deduces filename "2.7"
        # and unzip() falls back to the zip decoder → BadZipFile.  Pass an
        # explicit *.tar.gz filename so unzip() selects the tar.gz decoder
        # (abcmidi 20260609 precedent).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="kerberos-configs-2.7.tar.gz")

    def build(self):
        # Packaging-only recipe: upstream has no build system (debian/rules
        # merely cats debconf scripts for the Debian installer; nothing to
        # compile for HarmonyOS). The config payload is installed as-is.
        pass

    def package(self):
        # Main payload (mirrors debian/krb5-config.install):
        #   krb5.conf.template -> usr/share/kerberos-configs
        share = os.path.join(self.package_folder, "share", "kerberos-configs")
        copy(self, "krb5.conf.template", src=self.source_folder, dst=share)

        # Realm-parsing helper referenced by the upstream debconf tooling;
        # shipped so consumers (e.g. installer scripts) can reuse it.
        copy(self, "krb5confparse.pl", src=self.source_folder, dst=share)

        # Docs (mirrors debian/krb5-config.docs): README, packaging-guidelines
        copy(self, "README", src=self.source_folder, dst=share)
        copy(self, "packaging-guidelines", src=self.source_folder, dst=share)

    def package_info(self):
        # Pure config/data package: no C/C++ libraries or binaries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/kerberos-configs"]
