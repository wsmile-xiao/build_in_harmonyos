#!/usr/bin/env python3
"""Conan recipe — moon-buggy 1.1.0 — Autotools build system.

moon-buggy is a simple character graphics game, where you drive some
kind of car across the moon's surface. Unfortunately there are
dangerous craters there. Fortunately your car can jump over them!
Source: https://www.seehuhn.de/programs/moon-buggy
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MoonBuggyConan(ConanFile):
    name = "moon-buggy"
    version = "1.1.0"
    description = "Drive some car across the moon - a simple character graphics game"
    license = "GPL-2.0-or-later OR GPL-3.0-or-later"
    homepage = "https://www.seehuhn.de/programs/moon-buggy"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # ncurses/6.5 默认启用宽字符（--enable-widec 硬编码），
        # options 仅有 shared/fPIC，无需 with_widec
        self.requires("ncurses/6.5", options={"shared": False})

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"moon-buggy supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        ncurses = self.dependencies["ncurses"].cpp_info
        ncurses_core = next(
            (
                lib
                for lib in ncurses.libs
                if lib.startswith("ncurses") and not lib.startswith("ncurses++")
            ),
            None,
        )
        if ncurses_core is None or not ncurses.includedirs or not ncurses.libdirs:
            raise ConanInvalidConfiguration(
                "ncurses dependency does not export a usable core library"
            )

        ncurses_include = ncurses.includedirs[0]
        ncurses_lib = ncurses.libdirs[0]
        ncurses_archive = os.path.join(ncurses_lib, f"lib{ncurses_core}.a")
        if not os.path.isfile(ncurses_archive):
            raise ConanInvalidConfiguration(
                f"ncurses static archive not found: {ncurses_archive}"
            )

        if self.settings.os in ("OHOS",):
            # OHOS cross-compile host triplet
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            # config.guess 不认识 HarmonyOS (UNAME_SYSTEM=HarmonyOS)，显式指定 --build
            # 绕过 config.guess 猜测，避免 "cannot guess build type" 错误
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

        tc.extra_cflags.append(f"-I{ncurses_include}")
        tc.extra_ldflags.append(f"-L{ncurses_lib}")
        tc.configure_args.append(f"--with-curses-libs={ncurses_archive}")
        tc.configure_args.append("--with-curses-header=<ncurses.h>")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os in ("OHOS",):
            configure_path = os.path.join(self.source_folder, "configure")
            # E165: Fix shebang (no /bin/sh on OHOS)
            replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh")
            # E114: Fix HMDFS temp dir permission issue
            # config.status creates temp awk scripts (subs1.awk) in ./confXXXXXX
            # via mktemp -d, but HMDFS sets setgid+umask 077 making the dir
            # drwx--S--- which blocks file creation → "Permission denied".
            # Patch configure (embeds the config.status template) to use a
            # fixed temp directory instead of mktemp-generated one.
            import tempfile
            fixed_tmp = os.path.join(tempfile.gettempdir(), "moon-buggy-conan-fixed")
            os.makedirs(fixed_tmp, exist_ok=True)
            replace_in_file(self, configure_path, "ac_tmp=$tmp",
                            f"ac_tmp={fixed_tmp}")

        autotools = Autotools(self)
        autotools.configure()

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # install-data would regenerate Texinfo documentation, but the device
        # has no makeinfo. Install the executable target, then copy the release
        # info file and generated man page without invoking that rule.
        autotools.install(target="install-exec", args=["-j1"])
        copy(
            self,
            "moon-buggy.info",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "info"),
        )
        copy(
            self,
            "moon-buggy.6",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man6"),
        )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os in ("OHOS",):
            binary = os.path.join(self.package_folder, "bin", "moon-buggy")
            signed = binary + ".signed"
            objcopy = shutil.which("llvm-objcopy")
            signer = shutil.which("binary-sign-tool")
            if not objcopy or not signer:
                raise ConanInvalidConfiguration(
                    "OHOS packaging requires llvm-objcopy and binary-sign-tool in PATH"
                )
            self.run(
                f'"{objcopy}" --remove-section .codesign "{binary}"',
                ignore_errors=True,
            )
            self.run(
                f'"{signer}" sign -inFile "{binary}" '
                f'-outFile "{signed}" -selfSign 1'
            )
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    def package_info(self):
        # moon-buggy is a CLI game binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
