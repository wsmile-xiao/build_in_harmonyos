#!/usr/bin/env python3
"""Conan test_package — wmcube 1.0.2 (L1 official test, R34 real-artifact check).

wmcube is an X11 dockapp and a CI worker has no X server, so the harness does
not try to open a window.  It inspects the *packaged binary* instead: ELF
machine, the DT_NEEDED closure (which must contain libX11, libXext and
libXpm — the three libraries upstream's LIBS line asks for), and the
command-line surface plus version string that must have been compiled in.

The test source is compiled directly with the profile compiler (no CMake
generator) — the same shape as the asmix/coolmail precedents, which avoids
CMakePresets issues for executable-only packages.
"""
import os

from conan import ConanFile


class WmcubeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        bin_path = os.path.join(
            self.dependencies["wmcube"].package_folder, "bin", "wmcube"
        )
        self.output.info(f"packaged wmcube binary: {bin_path}")

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # Single quotes keep the embedded double quotes intact for the shell.
        self.run(f"{cc} -O2 -Wall test.c -o test_wmcube "
                 f"-D'WMCUBE_BIN=\"{bin_path}\"'")

    def test(self):
        # L0d: the harness must actually be executed, and it exits non-zero
        # when any of its 16 assertions fails.
        self.run("./test_wmcube")
