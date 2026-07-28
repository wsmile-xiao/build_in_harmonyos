#!/usr/bin/env python3
"""Conan recipe — libax25 0.0.12-rc5 (Autotools).

AX.25 amateur radio protocol library (AX.25/ROSE/NET/ROM).
"""
import os
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libax25Conan(ConanFile):
    name = "libax25"
    version = "0.0.12-rc5"
    description = "AX.25 amateur radio protocol library"
    license = "LGPL-2.1-or-later"
    homepage = "https://linux-ax25.in-berlin.de/wiki/Libax25"
    url = "https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/tree/main/archives/l/libax25/0.0.12-rc5"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}  # R26: system-name library defaults to static

    # Pre-generated autotools files (configure, Makefile.in, etc.) because
    # the source tarball only has configure.ac + Makefile.am (no configure script),
    # and CI machines may not have autotools installed.
    exports = "autotools-generated.tar.gz"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        # In-source build: source and build in the same directory
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported os: {self.settings.os}")

    def source(self):
        # Tarball has files at root level (no wrapping directory)
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static to avoid polluting /lib
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Extract pre-generated autotools files (configure, Makefile.in, etc.)
        # The source tarball only has configure.ac + Makefile.am, no configure script.
        # We pre-generate these locally because CI machines may lack autotools.
        tarball = os.path.join(self.recipe_folder, "autotools-generated.tar.gz")
        if os.path.exists(tarball):
            with tarfile.open(tarball, "r:gz") as tf:
                tf.extractall(self.source_folder)
        else:
            # Fallback: try autoreconf if available
            self.run("autoreconf --install --force", env="conanbuild")

        # E165: Fix shebangs for OHOS (no /bin/sh or /bin/bash on OHOS)
        for script in ["configure", "config.status", "libtool",
                       "compile", "missing", "depcomp", "ltmain.sh"]:
            self.run(
                f"sed -i '1s|#!/bin/sh|#!/system/bin/sh|' {script} 2>/dev/null || true",
                env="conanbuild",
            )
            self.run(
                f"sed -i '1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' {script} 2>/dev/null || true",
                env="conanbuild",
            )

        # E007: Patch config.guess/config.sub for OHOS platform detection.
        self._patch_config_for_ohos()

        # HMDFS compatibility: remove umask 077 from generated scripts.
        self.run(
            r"""sed -i 's/umask 077 && mktemp -d/mktemp -d/g' configure""",
            env="conanbuild",
        )
        self.run(
            r"""sed -i 's/(umask 077 && mkdir/(mkdir/g' configure""",
            env="conanbuild",
        )
        self.run(
            r"""sed -i 's/umask 0077/umask 0000/g' libtool 2>/dev/null || true""",
            env="conanbuild",
        )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_config_for_ohos(self):
        """Patch config.guess/config.sub for HarmonyOS/OHOS platform detection."""
        if self.settings.os != "OHOS":
            return

        arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
        arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        triplet = f"{arch}-unknown-linux-ohos"

        config_guess = os.path.join(self.source_folder, "config.guess")
        with open(config_guess, "w") as f:
            f.write("#!/system/bin/sh\n")
            f.write("# Patched by conanfile.py for OHOS (E007)\n")
            f.write(f'echo "{triplet}"\n')
        os.chmod(config_guess, 0o755)

        config_sub = os.path.join(self.source_folder, "config.sub")
        with open(config_sub, "w") as f:
            f.write("#!/system/bin/sh\n")
            f.write("# Patched by conanfile.py for OHOS (E007)\n")
            f.write('echo "$1"\n')
        os.chmod(config_sub, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Ensure ALL headers are installed (configure may skip netax25/ax25.h,
        # netrom/netrom.h, netrose/rose.h if system headers exist)
        for subdir in ["netax25", "netrom", "netrose"]:
            copy(self, "*.h",
                 os.path.join(self.source_folder, subdir),
                 os.path.join(self.package_folder, "include", subdir))

    def package_info(self):
        self.cpp_info.libs = ["ax25", "ax25io"]
