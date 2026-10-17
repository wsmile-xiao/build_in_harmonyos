#!/usr/bin/env python3
"""Conan recipe for less 661 — Autotools (configure + make).

less is a terminal pager program for Unix systems.
On HarmonyOS, requires ncurses/6.5 for terminal support.
"""
import os

from conan import ConanFile
from conan.tools.files import get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LessConan(ConanFile):
    name = "less"
    version = "661"
    description = "Terminal pager program similar to more"
    license = "GPL-3.0-or-later"
    homepage = "https://www.greenwoodsoftware.com/less/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsDeps"

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
        env.vars(self).save_script("less_shell_env")

    def _patch_configure_umask(self):
        """E011: HMDFS umask 077 fix (debugedit/cloog/dfu/dhcpcd pattern).

        config.status creates its temp dir via ``umask 077 && mktemp -d``;
        on HMDFS the resulting dir (drwx--S---) is not writable by the
        build process, so ``subs1.awk`` creation fails with Permission
        denied. The temp-dir block lives inside configure's config.status
        template, so patching configure propagates to config.status.
        configure is a generated file and cannot be a conandata patch.
        """
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        text = load(self, cfg)
        changed = False
        if "umask 000" not in text:
            nl = text.find("\n")
            text = text[: nl + 1] + "umask 000\n" + text[nl + 1:]
            changed = True
        for old, new in (
            ('(umask 077 && mktemp -d "./confXXXXXX")',
             '(umask 000 && mktemp -d "./confXXXXXX")'),
            ('(umask 077 && mkdir "$tmp")', '(umask 000 && mkdir "$tmp")'),
        ):
            if old in text:
                text = text.replace(old, new)
                changed = True
        if changed:
            save(self, cfg, text)
            self.output.info("patched configure: umask 077->000 (E011 HMDFS)")

    def build(self):
        self._patch_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
