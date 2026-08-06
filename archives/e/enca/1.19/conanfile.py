#!/usr/bin/env python3
"""Conan recipe for enca 1.19 — Charset analyser and converter.

enca (Extremely Naive Charset Analyser) provides libenca, an encoding
detection library, and the enca command-line tool.

Adaptation notes for HarmonyOS:
- config.guess: added HarmonyOS detection (aarch64:HarmonyOS -> aarch64-unknown-linux-ohos)
- config.sub: added linux-ohos* to maybe_os and OS validation list
- configure: changed umask 077 to umask 022 (E206: HMDFS setgid directory permissions)
- src/filebuf.c: replaced hardcoded /tmp with TMPDIR env var (E002: /tmp read-only)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EncaConan(ConanFile):
    name = "enca"
    version = "1.19"
    description = "Extremely Naive Charset Analyser — encoding detection library and tool"
    license = "GPL-2.0-only"
    homepage = "https://github.com/nijel/enca"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libiconv/1.17")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["enca"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
