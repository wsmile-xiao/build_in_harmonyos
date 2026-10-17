#!/usr/bin/env python3
"""Conan recipe — wolfssl 5.7.0 (Autotools)

Embedded SSL/TLS Library written in C.
Platform adaptations: E010 (CONFIG_SHELL=bash via profile buildenv),
E011 (umask fix for HMDFS temp dirs), E004 (LD_LIBRARY_PATH via profile buildenv).
Based on the verified wolfssl 4.6.0 recipe; version bumped to 5.7.0.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WolfsslConan(ConanFile):
    name = "wolfssl"
    version = "5.7.0"
    description = "Embedded SSL/TLS Library written in C"
    license = "GPL-2.0-or-later"
    homepage = "https://www.wolfssl.com/"
    url = "https://github.com/wolfSSL/wolfssl"

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
        # E007: config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS").
        # Pass the triplet explicitly (config.sub supports *-linux-ohos) so
        # configure never runs the config.guess probe; --build == --host so
        # it stays native (AC_RUN_IFELSE still executes).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive 不包含生成的 configure，需 autoreconf 生成
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
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["wolfssl"]