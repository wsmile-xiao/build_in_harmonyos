#!/usr/bin/env python3
"""Conan recipe for acf-openssl 0.11.0 (Alpine ACF Lua web admin module).

Pure Lua/LSP script package — no compilation. Installs the openssl ACF app
module (controllers/model/html templates/roles/menu) into share/acf/app/openssl.

Upstream: https://gitlab.alpinelinux.org/acf/acf-openssl
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfOpensslConan(ConanFile):
    name = "acf-openssl"
    version = "0.11.0"
    description = "Web-based system administration interface for openssl (ACF module)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-openssl"
    url = ""
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        # ACF app module layout: $(datadir)/acf/app/openssl
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "openssl")
        os.makedirs(appdir, exist_ok=True)

        # APP_DIST from upstream Makefile: openssl*.lua openssl*.lsp openssl.roles openssl.menu
        for pattern in ("openssl*.lua", "openssl*.lsp", "openssl.roles", "openssl.menu"):
            copy(self, pattern, src=self.source_folder, dst=appdir, keep_path=False)

        # ETC_DIST: openssl-ca-acf.cnf -> share/acf/openssl/
        etcdir = os.path.join(self.package_folder, "share", "acf", "openssl")
        os.makedirs(etcdir, exist_ok=True)
        copy(self, "openssl-ca-acf.cnf", src=self.source_folder, dst=etcdir, keep_path=False)

        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/acf"]
