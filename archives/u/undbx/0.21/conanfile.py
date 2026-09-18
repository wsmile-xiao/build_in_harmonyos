#!/usr/bin/env python3
"""Conan recipe for UnDBX 0.21.

UnDBX is a command-line extractor/recovery tool for Outlook Express DBX files.
The GitHub source snapshot needs an Autotools bootstrap before configuration.
"""
import os
import re
import stat
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UndbxConan(ConanFile):
    name = "undbx"
    version = "0.21"
    description = "Command-line extractor and recovery tool for Outlook Express DBX files"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/ZungBang/undbx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # The GitHub snapshot has no generated configure script, so autoreconf
        # needs aclocal/automake.  The device's Harmonybrew PATH masks this
        # requirement locally, but the CI worker only provides autoconf.
        self.tool_requires("automake/1.18")

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        tc.generate()

    def _patch_autotools_scripts(self):
        """Teach generated config.guess/config.sub the native OHOS tuple (E007)."""
        guess_path = os.path.join(self.source_folder, "config.guess")
        sub_path = os.path.join(self.source_folder, "config.sub")

        with open(guess_path, encoding="utf-8") as handle:
            guess = handle.read()
        if "__OHOS__" not in guess:
            guess, count = re.subn(
                r"(^[ \t]*#[ \t]*if[ \t]+defined\(__ANDROID__\)[ \t]*\n[ \t]*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                guess,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise RuntimeError("config.guess: Android libc detection anchor not found")
        if "HarmonyOS" not in guess:
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
            )
            guess, count = re.subn(
                r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                block + r"\1",
                guess,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise RuntimeError("config.guess: NetBSD insertion anchor not found")
        with open(guess_path, "w", encoding="utf-8") as handle:
            handle.write(guess)

        with open(sub_path, encoding="utf-8") as handle:
            sub = handle.read()
        if "ohos-linux)" not in sub:
            pattern = (
                r"(^[ \t]*android-linux\)[ \t]*\n)"
                r"([ \t]*basic_machine=\$field1-unknown[ \t]*\n)"
                r"([ \t]*basic_os=linux-android[ \t]*\n)"
                r"([ \t]*;;[ \t]*\n)"
            )

            def add_ohos_triplet(match):
                indent = re.match(r"[ \t]*", match.group(1)).group(0)
                return (
                    match.group(0)
                    + f"{indent}ohos-linux)\n"
                    + f"{indent}\tbasic_machine=$field1-unknown\n"
                    + f"{indent}\tbasic_os=linux-ohos\n"
                    + f"{indent}\t;;\n"
                )

            sub, count = re.subn(pattern, add_ohos_triplet, sub, count=1, flags=re.MULTILINE)
            if count != 1:
                raise RuntimeError("config.sub: Android triplet anchor not found")
        if "linux-ohos" not in sub:
            sub, count = re.subn(
                r"(linux-uclibc\*[/-]?[ \t]*)\)",
                r"\1| linux-ohos*)",
                sub,
                count=1,
            )
            if count != 1:
                raise RuntimeError("config.sub: kernel/OS validation anchor not found")
        with open(sub_path, "w", encoding="utf-8") as handle:
            handle.write(sub)

        shell = os.environ.get("SHELL", "/bin/sh")
        if not os.path.isabs(shell) or not os.path.isfile(shell):
            shell = "/bin/sh"
        result = subprocess.run(
            [shell, sub_path, "aarch64-unknown-linux-ohos"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or result.stdout.strip() != "aarch64-unknown-linux-ohos":
            raise RuntimeError(
                f"config.sub rejected native OHOS tuple: {result.stdout.strip()!r}"
            )

    def _fix_hmdfs_umask(self):
        """Keep Autoconf temporary directories group-writable on HMDFS (E011/E114)."""
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 002",
            strict=True,
        )

    def _restore_autotools_modes(self):
        """Restore execute bits only on known Autotools helper scripts (E490)."""
        for name in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            mode = os.stat(path).st_mode
            os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _configure_with_safe_shell(self, autotools):
        """Run configure through /bin/sh while retaining Conan's build environment (E386)."""
        configure_path = os.path.join(self.source_folder, "configure")
        configure_args = getattr(autotools, "_configure_args", "")
        command = (
            f'env -u CONFIG_SHELL SHELL=/bin/sh /bin/sh "{configure_path}" '
            f"{configure_args}"
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # The codeload snapshot contains configure.ac/Makefile.am but no configure.
        autotools.autoreconf(build_script_folder=self.source_folder)
        self._restore_autotools_modes()
        self._patch_autotools_scripts()
        self._fix_hmdfs_umask()
        self._configure_with_safe_shell(autotools)
        autotools.make(args=["-j1"])
        # Upstream has no registered test programs; keep the official target in the recipe.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
