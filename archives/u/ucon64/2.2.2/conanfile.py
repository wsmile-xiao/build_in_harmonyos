#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Ucon64, ucon64, 2.2.2, ucon64 2.2.2, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Ucon64Conan(ConanFile):
    name = "ucon64"
    version = "2.2.2"
    description = "uCON64 - the Universal Console file and backup tool"
    license = "GPL-2.0-or-later"
    homepage = "https://ucon64.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Tarball has nested src/ directory — promote to top level
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            for item in os.listdir(src_dir):
                shutil.move(os.path.join(src_dir, item),
                            os.path.join(self.source_folder, item))
            os.rmdir(src_dir)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Disable parallel port support (no I/O port access on aarch64)
        tc.configure_args.append("--disable-parallel")
        tc.generate()

    def _patch_config_guess_sub(self):
        """Patch config.guess and config.sub in-place for HarmonyOS support (E007).

        The original 2017 config.guess uses echo/exit format (not GUESS=).
        We patch it to recognize HarmonyOS as aarch64-unknown-linux-ohos.
        """
        cg_path = os.path.join(self.source_folder, "config.guess")
        cs_path = os.path.join(self.source_folder, "config.sub")

        # --- Patch config.guess (2017 format: echo + exit) ---
        if os.path.exists(cg_path):
            with open(cg_path, "r") as f:
                cg = f.read()
            changed = False

            # 1. Add __OHOS__ LIBC detection in the features.h block
            if "__OHOS__" not in cg:
                cg = cg.replace(
                    "#elif defined(__dietlibc__)\n\tLIBC=dietlibc\n\t#else",
                    "#elif defined(__dietlibc__)\n\tLIBC=dietlibc\n#elif defined(__OHOS__)\n\tLIBC=ohos\n\t#else"
                )
                changed = True

            # 2. Add HarmonyOS case block before NetBSD (2017 format: echo + exit)
            if "HarmonyOS" not in cg:
                block = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "${UNAME_MACHINE}" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    i?86)         MACHINE=i686 ;;\n'
                    '\t    *)            MACHINE="${UNAME_MACHINE}" ;;\n'
                    '\tesac\n'
                    '\techo ${MACHINE}-unknown-linux-ohos\n'
                    '\texit ;;\n'
                )
                cg = cg.replace("    *:NetBSD:*:*)", block + "    *:NetBSD:*:*)")
                changed = True

            if changed:
                with open(cg_path, "w") as f:
                    f.write(cg)

        # --- Patch config.sub (2017 format) ---
        if os.path.exists(cs_path):
            with open(cs_path, "r") as f:
                cs = f.read()
            changed = False

            # 1. Add linux-ohos* to OS type list (after linux-uclibc*)
            if "linux-ohos" not in cs:
                cs = cs.replace(
                    "linux-musl* | linux-uclibc*",
                    "linux-musl* | linux-uclibc* | linux-ohos*"
                )
                changed = True

            # 2. Add ohos-linux to android-linux case (shares same handling)
            if "ohos-linux" not in cs:
                cs = cs.replace("android-linux)", "android-linux | ohos-linux)")
                changed = True

            # 3. Add -linux-ohos* to OS validation list
            if "-linux-ohos*" not in cs:
                cs = cs.replace(
                    "-linux-musl* | -linux-uclibc*",
                    "-linux-musl* | -linux-uclibc* | -linux-ohos*"
                )
                changed = True

            if changed:
                with open(cs_path, "w") as f:
                    f.write(cs)

    def build(self):
        apply_conandata_patches(self)
        # Patch config.guess/config.sub for HarmonyOS (E007)
        self._patch_config_guess_sub()
        # Patch umask 077 → 022 in configure (HMDFS permission issue on HarmonyOS)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)
        # Run configure and make in-tree (ucon64 doesn't support out-of-tree builds)
        # Use -j1 to avoid mkfifo jobserver issues on HMDFS
        prefix = self.package_folder.replace("\\", "/")
        # Pass standard autotools args + project-specific --disable-parallel
        # LDFLAGS with -static comes from generate() via AutotoolsToolchain env
        configure_cmd = (
            f'./configure --prefix={prefix} '
            f"--bindir=${{prefix}}/bin "
            f"--sbindir=${{prefix}}/bin "
            f"--libdir=${{prefix}}/lib "
            f"--includedir=${{prefix}}/include "
            f"--disable-parallel"
        )
        self.run(configure_cmd, cwd=self.source_folder)
        self.run('make -j1', cwd=self.source_folder)

    def package(self):
        # ucon64's install.sh uses sudo and hardcoded paths, so copy manually
        # Binary is built in-tree (source_folder)
        copy(self, "ucon64", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Terminal tool: no libraries to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
