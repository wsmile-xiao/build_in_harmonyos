#!/usr/bin/env python3
"""Conan recipe for isync (mbsync) — IMAP and MailDir mailbox synchronizer."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class IsyncConan(ConanFile):
    name = "isync"
    version = "1.5.1"
    description = "IMAP and MailDir mailbox synchronizer (mbsync)"
    license = "GPL-2.0-or-later"
    homepage = "https://isync.sourceforge.net/"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("isync is supported only on Linux/OHOS")

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        # OHOS: umask 077 causes permission denied on config.status temp files
        os.umask(0)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
