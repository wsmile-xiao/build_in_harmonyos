#!/usr/bin/env python3
"""Conan recipe for libplist 2.3.0 — Apple Property List library.

libplist is a C/C++ library to handle Apple Property List files in
binary and XML format. It provides both C (plist.h) and C++ (plist++.h)
APIs. The pkg-config name is libplist-2.0.

Dependencies: none (leaf library).
License: LGPL-2.1+
Homepage: https://libimobiledevice.org/

OHOS adaptations:
  - mktemp wrapper: autoconf AS_TMPDIR uses `umask 077 && mktemp -d`
    which creates dirs with drwx--S--- on HMDFS (setgid + MAC), causing
    config.status to fail writing subs*.awk. A fake mktemp that returns
    failure forces the mkdir fallback (E114).
  - --build=aarch64-unknown-linux-gnu: config.guess doesn't recognize OHOS.
  - --without-cython: disable Python bindings (not needed for C/C++ library).
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibplistConan(ConanFile):
    name = "libplist"
    version = "2.3.0"
    description = "A library to handle Apple Property List files (binary and XML)"
    license = "LGPL-2.1+"
    homepage = "https://libimobiledevice.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libplist is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Leaf library — no third-party dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail writing subs*.awk. Create a mktemp wrapper
        # that returns failure to force autoconf AS_TMPDIR to use mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # HarmonyOS: config.guess doesn't recognize the OS, force build triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # Disable Python bindings (not needed for C/C++ library)
        tc.configure_args.append("--without-cython")
        # R26: static linking for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # pkg-config name is libplist-2.0
        self.cpp_info.set_property("cmake_file_name", "libplist-2.0")
        self.cpp_info.set_property("pkg_config_name", "libplist-2.0")
        self.cpp_info.libs = ["plist-2.0"]
