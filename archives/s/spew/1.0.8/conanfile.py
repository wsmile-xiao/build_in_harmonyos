#!/usr/bin/env python3
"""Conan recipe — spew 1.0.8 (Autotools).

spew is an I/O performance measurement and load generation tool.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpewConan(ConanFile):
    name = "spew"
    version = "1.0.8"
    description = "I/O performance measurement and load generation tool"
    license = "GPL-2.0-only"
    homepage = "https://github.com/apatters/spew"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("popt/1.16")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # The tag is a VCS archive without generated configure/Makefile.in.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"unsupported OS: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        get(self, **source, strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _prepare_sources(self):
        # ncurses/6.6 intentionally ships only the wide-character static ABI.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure.ac"),
            "AC_CHECK_LIB(ncurses, wresize",
            "AC_CHECK_LIB(ncursesw, wresize",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "spew.cpp"),
            "#include <unistd.h>\n",
            "#include <unistd.h>\n#include <libgen.h>\n",
        )

    def _patch_config_scripts(self):
        config_dir = os.path.join(self.source_folder, "config")
        guess_path = os.path.join(config_dir, "config.guess")
        sub_path = os.path.join(config_dir, "config.sub")

        with open(guess_path, "r", encoding="utf-8") as handle:
            guess = handle.read()
        if "HarmonyOS" not in guess:
            marker = "    *:NetBSD:*:*)"
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tGUESS=${UNAME_MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
            )
            if marker not in guess:
                raise ConanInvalidConfiguration(
                    "config.guess has no supported HarmonyOS insertion point"
                )
            guess = guess.replace(marker, block + marker, 1)
            with open(guess_path, "w", encoding="utf-8") as handle:
                handle.write(guess)

        result = subprocess.run(
            [sub_path, "aarch64-unknown-linux-ohos"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode != 0 or "linux-ohos" not in result.stdout:
            raise ConanInvalidConfiguration(
                "config.sub does not accept the OHOS triplet: " + result.stdout
            )

    def _patch_generated_configure(self):
        # E011: on HMDFS the `umask 077 && mktemp -d "./confXXXXXX"` block in
        # config.status produces a setgid directory owned by another uid, so the
        # generated subs*.awk cannot be executed (Permission denied).
        for name in ("configure", "config.status"):
            path = os.path.join(self.source_folder, name)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                script = handle.read()
            patched = script.replace("umask 077", "umask 022")
            if patched != script:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(patched)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_sources()
        autotools = Autotools(self)
        autotools.autoreconf(args=["-fi"])
        self._patch_config_scripts()
        self._patch_generated_configure()
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream 1.0.8 registers no TESTS/check_PROGRAMS; this still executes
        # the complete upstream check target and records its zero-test result.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        built = os.path.join(self.build_folder, "src", "spew")
        copy(self, "spew", src=os.path.dirname(built), dst=bindir, keep_path=False)
        for alias in ("gorge", "regorge"):
            shutil.copy2(os.path.join(bindir, "spew"), os.path.join(bindir, alias))
        copy(self, "spew.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
