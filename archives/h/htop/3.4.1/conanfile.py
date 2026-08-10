#!/usr/bin/env python3
"""Conan recipe for htop 3.4.1 — Autotools (configure + make).

htop is an interactive process viewer for Unix systems.
On HarmonyOS, requires ncurses/6.5 (static) and platform patches.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class HtopConan(ConanFile):
    name = "htop"
    version = "3.4.1"
    description = "Interactive process viewer for Unix systems"
    license = "GPL-2.0"
    homepage = "https://htop.dev/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

        # HarmonyOS: use bash as CONFIG_SHELL
        # /bin/sh (toybox) cannot access mktemp-created dirs due to permission model
        env = Environment()
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("SHELL", "/data/service/hnp/bin/bash")
        # Override LIBS to empty: AutotoolsDeps puts ncurses in LIBS which
        # breaks the basic compiler test (conftest can't link with ncurses).
        # htop's configure uses NCURSES_LIBS for ncurses detection, not LIBS.
        # LDFLAGS (with -L path) and CPPFLAGS (with -I path) are preserved.
        env.define("LIBS", "")
        env.vars(self).save_script("htop_shell_env")

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS: fix umask 077 → 022 in configure
        # mktemp -d with umask 077 creates dirs that the build user cannot access
        configure_path = os.path.join(self.source_folder, "configure")
        self.run(f"sed -i 's/umask 077/umask 022/g' '{configure_path}'")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
