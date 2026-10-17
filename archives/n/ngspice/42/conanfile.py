#!/usr/bin/env python3
"""Conan recipe — ngspice 42 (Autotools).

ngspice is a mixed-level/mixed-signal circuit simulator based on SPICE3f5.
Builds as a standalone executable (no shared library by default).

This recipe enforces R26: static linking for system-name libraries.
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class NgspiceConan(ConanFile):
    name = "ngspice"
    version = "42"
    description = "Mixed-level/mixed-signal circuit simulator based on SPICE3f5"
    license = "BSD-3-Clause"
    homepage = "https://ngspice.sourceforge.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC),
        # causing config.status to fail. Create a mktemp wrapper that forces
        # autoconf AS_TMPDIR to use mkdir fallback.
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
        tc.configure_args.extend([
            "--disable-debug",
            "--with-readline=no",
            "--with-ngshared=no",
            "--without-x",
        ])
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
