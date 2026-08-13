#!/usr/bin/env python3
"""Conan recipe — wolfssl 4.6.0 (Autotools)

Embedded SSL/TLS Library written in C.
Platform adaptations: E010 (CONFIG_SHELL=bash), E011 (umask fix), E004 (LD_LIBRARY_PATH).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WolfsslConan(ConanFile):
    name = "wolfssl"
    version = "4.6.0"
    description = "Embedded SSL/TLS Library written in C — 轻量级嵌入式 SSL/TLS 库"
    license = "GPL-3.0-or-later"
    homepage = "https://www.wolfssl.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # CI workers lack aclocal and libtool m4 macros
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

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
        # E007: config.guess doesn't recognize OHOS; specify triplet explicitly
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # E010: CONFIG_SHELL is set via Conan profile buildenv
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf()
        # E011: HMDFS umask 077 causes temp dir permission errors
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        autotools.configure()
        # E011 supplemental: fix config.status after configure generates it
        config_status = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(config_status):
            replace_in_file(self, config_status, "umask 077", "umask 022")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["wolfssl"]
