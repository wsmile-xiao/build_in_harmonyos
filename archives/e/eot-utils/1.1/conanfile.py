#!/usr/bin/env python3
"""Conan recipe for eot-utils 1.1 — W3C EOT font utilities (mkeot, eotinfo).

Autotools project, pure C, no third-party dependencies.
Produces two command-line tools: mkeot (TTF→EOT) and eotinfo (EOT header info).
License: MIT (see COPYING in source)
Homepage: https://www.w3.org/Tools/eot-utils/
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class EotUtilsConan(ConanFile):
    name = "eot-utils"
    version = "1.1"
    description = "W3C EOT font utilities — mkeot (TTF/OTF→EOT) and eotinfo (EOT header info)"
    license = "MIT"
    homepage = "https://www.w3.org/Tools/eot-utils/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: autoconf 2.68's config.status uses umask 077 for temp dirs.
        # On HMDFS, process uid != file owner uid, so owner-only dirs are
        # inaccessible. Create a mktemp wrapper that returns failure to force
        # autoconf AS_TMPDIR to use the mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms on HMDFS.\n'
            '# Return failure to force autoconf AS_TMPDIR mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # Force build triplet since source lacks config.guess/config.sub
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

        # Prepend wrapper to PATH so configure uses our mktemp
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def build(self):
        # Apply umask 077→007 patch for HMDFS compatibility
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tools, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
