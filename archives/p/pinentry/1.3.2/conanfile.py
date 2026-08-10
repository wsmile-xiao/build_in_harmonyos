#!/usr/bin/env python3
"""Conan recipe — pinentry 1.3.2 (autotools, command-line tool).

pinentry is a collection of PIN/pass-phrase entry dialogs for GnuPG.
This recipe builds pinentry-curses and pinentry-tty frontends for HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PinentryConan(ConanFile):
    name = "pinentry"
    version = "1.3.2"
    description = "GnuPG PIN entry dialog for entering passwords and other sensitive data"
    license = "GPL-2.0-or-later"
    homepage = "https://gnupg.org/related_software/pinentry/index.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libgpg-error/1.55")
        self.requires("libassuan/3.0.2")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-pinentry-curses",
            "--enable-pinentry-tty",
            "--disable-pinentry-efl",
            "--disable-pinentry-qt",
            "--disable-pinentry-qt4",
            "--disable-pinentry-qt5",
            "--disable-pinentry-tqt",
            "--disable-inside-emacs",
            "--disable-fallback-curses",
        ])
        tc.generate()

    def _fix_shebang(self, path):
        """Replace /bin/sh shebang with /data/service/hnp/bin/bash for HarmonyOS."""
        if not os.path.isfile(path):
            return
        with open(path, "r") as f:
            content = f.read()
        if content.startswith("#!/bin/sh"):
            with open(path, "w") as f:
                f.write("#!/data/service/hnp/bin/bash\n")
                rest = content[len("#!/bin/sh"):]
                if rest.startswith("\n"):
                    rest = rest[1:]
                f.write(rest)

    def _build_environment(self):
        """Create build environment with dependency paths."""
        gpg_error = self.dependencies["libgpg-error"]
        libassuan = self.dependencies["libassuan"]
        ncurses = self.dependencies["ncurses"]

        gpg_error_bin = os.path.join(gpg_error.package_folder, "bin")
        libassuan_bin = os.path.join(libassuan.package_folder, "bin")

        # Fix shebang of config scripts (HarmonyOS /bin/sh is broken)
        for script in ["gpgrt-config", "gpg-error-config"]:
            self._fix_shebang(os.path.join(gpg_error_bin, script))
        self._fix_shebang(os.path.join(libassuan_bin, "libassuan-config"))

        env = AutotoolsToolchain(self).environment()
        env.compose_env(AutotoolsDeps(self).vars())

        local_env = Environment()
        local_env.prepend_path("PATH", gpg_error_bin)
        local_env.prepend_path("PATH", libassuan_bin)
        local_env.prepend_path("LD_LIBRARY_PATH", os.path.join(gpg_error.package_folder, "lib"))
        local_env.prepend_path("LD_LIBRARY_PATH", os.path.join(libassuan.package_folder, "lib"))
        local_env.prepend_path("LD_LIBRARY_PATH", os.path.join(ncurses.package_folder, "lib"))

        # Set config script paths so configure finds them directly
        gpgrt_config = os.path.join(gpg_error_bin, "gpgrt-config")
        if os.path.isfile(gpgrt_config):
            local_env.define("GPGRT_CONFIG", gpgrt_config)
        libassuan_config = os.path.join(libassuan_bin, "libassuan-config")
        if os.path.isfile(libassuan_config):
            local_env.define("LIBASSUAN_CONFIG", libassuan_config)

        # Use build-folder-relative TMPDIR for portability
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        local_env.define("TMPDIR", tmpdir)
        local_env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        local_env.define("SHELL", "/data/service/hnp/bin/bash")

        env.compose_env(local_env)
        return env.vars(self)

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 -> 022 in generated configure (HarmonyOS HMDFS permission issue)
        # R6: use Conan API replace_in_file instead of manual file I/O
        replace_in_file(self, os.path.join(self.source_folder, "configure"), "umask 077", "umask 022")
        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
