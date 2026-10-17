#!/usr/bin/env python3
"""Conan recipe for coreutils-fmt 9.11 — GNU coreutils fmt text formatter.

Extracts only the `fmt` binary from GNU coreutils 9.11.
Build system: autotools (configure + make).
Output: fmt binary (command-line tool, not a library).

Key adaptation:
- config.guess: add aarch64:HarmonyOS:* case
- gnulib freadahead.c: musl libc opaque FILE structure fallback
- mktemp wrapper: HarmonyOS HMDFS mktemp -d creates dirs with broken perms
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class CoreutilsFmtConan(ConanFile):
    name = "coreutils-fmt"
    version = "9.11"
    description = "GNU coreutils fmt — simple text formatter"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/coreutils/"
    url = "https://ftp.gnu.org/gnu/coreutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # coreutils-fmt has no external dependencies (pure C, only libc)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that forces
        # autoconf to use mkdir fallback.
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
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
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
        # Install only the fmt binary
        copy(self, "fmt", src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

        # R7: Self-sign ELF binary on OHOS for local execution
        if self.settings.os == "OHOS":
            fmt_path = os.path.join(self.package_folder, "bin", "fmt")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(fmt_path):
                signed_path = f"{fmt_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{fmt_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, fmt_path)
                    os.chmod(fmt_path, 0o755)

    def package_info(self):
        # fmt is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
