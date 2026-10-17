#!/usr/bin/env python3
"""Conan recipe for coreutils-env 9.11 — GNU coreutils env command.

coreutils-env = GNU coreutils 9.11 source, packages only the `env` binary.

R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
R33: compiler/flags come from Conan toolchain, no bare shell ${CC}/${CFLAGS}.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    get, save, load, apply_conandata_patches, export_conandata_patches,
    copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CoreutilsEnvConan(ConanFile):
    name = "coreutils-env"
    version = "9.11"
    description = "GNU coreutils env — run a program with a modified environment"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/coreutils/"
    url = "https://ftp.gnu.org/gnu/coreutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS profile 携带 os.version=6.0，但本包不依赖其值；
        # 移除以避免 OHOS 下 settings.os.version 未定义导致包无效。
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # coreutils has no external dependencies
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "coreutils-env is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-fPIC")
        tc.generate()

    def _fix_umask(self, path):
        """Fix umask 077 in configure/config.status for HMDFS compatibility.

        On HarmonyOS HMDFS, umask 077 in mktemp/mkdir creates directories
        where file creation fails with EACCES ("Permission denied" in
        config.status's ./confXXXX/subs1.awk). Replace umask 077 usage.
        """
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def build(self):
        apply_conandata_patches(self)

        # Fix configure script: umask 077 breaks on HMDFS (E046/E174)
        configure_path = os.path.join(self.source_folder, "configure")
        self._fix_umask(configure_path)

        autotools = Autotools(self)
        try:
            autotools.configure()
        except ConanException:
            # config.status may fail due to umask 077 in generated code
            pass

        # Fix config.status (generated file - cannot be a source patch)
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self._fix_umask(cs_path)
            self.run('cd "{}" && bash config.status'.format(self.build_folder))

        # Full build (BUILT_SOURCES generate configmake.h/stdckdint.h etc.)
        autotools.make(args=[
            "-j2",
            "ACLOCAL=true",
            "AUTOMAKE=true",
            "AUTOCONF=true",
            "AUTOHEADER=true",
            "MAKEINFO=true",
        ])

    def package(self):
        # 仅打包 env 命令（coreutils-env 的交付范围）
        mkdir = os.makedirs
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        mkdir(bin_dir, exist_ok=True)
        mkdir(man_dir, exist_ok=True)

        env_bin = os.path.join(self.build_folder, "src", "env")
        if not os.path.exists(env_bin):
            raise ConanException("src/env binary not found after build")
        copy(self, "env", os.path.join(self.build_folder, "src"), bin_dir)

        env_man = os.path.join(self.source_folder, "man", "env.1")
        if os.path.exists(env_man):
            copy(self, "env.1", os.path.join(self.source_folder, "man"), man_dir)

    def package_info(self):
        # command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure env binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
