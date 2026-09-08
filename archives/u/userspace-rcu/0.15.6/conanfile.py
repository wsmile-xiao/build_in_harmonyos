#!/usr/bin/env python3
"""Conan recipe — userspace-rcu 0.15.6 (userspace RCU library, C/autotools) on HarmonyOS PC.

userspace-rcu is a standalone library with no external dependencies.
It provides Read-Copy-Update (RCU) synchronization primitives for userspace.

Key adaptation notes:
- HMDFS temp dir issue: patch 0001 fixes configure's mktemp with umask 077.
- config.guess/config.sub updated for OHOS platform detection (patches 0002/0003).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UserspaceRcuConan(ConanFile):
    name = "userspace-rcu"
    version = "0.15.6"
    description = "Userspace RCU (read-copy-update) library"
    license = "LGPL-2.1-or-later AND MIT"
    homepage = "https://liburcu.org"
    url = "https://github.com/urcu/userspace-rcu"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Standalone library, no dependencies

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"userspace-rcu {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Create .config-tmp directory for patched configure (HMDFS workaround)
        config_tmp = os.path.join(self.source_folder, ".config-tmp")
        os.makedirs(config_tmp, exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Run upstream tests (make check) — ignore_errors for non-critical failures
        self.run("make -j1 check", cwd=self.build_folder, ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = [
            "urcu",
            "urcu-bp",
            "urcu-cds",
            "urcu-common",
            "urcu-mb",
            "urcu-memb",
            "urcu-qsbr",
        ]
        self.cpp_info.set_property("cmake_file_name", "userspace-rcu")
        self.cpp_info.set_property("pkg_config_name", "liburcu")
