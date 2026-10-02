#!/usr/bin/env python3
"""Conan test_package for swapspace 1.18 — consumer verification.

Runs the real installed `swapspace` binary through test_swapspace.sh,
which asserts version/help output, option parsing, configuration file
handling, numeric range validation and swap-directory probing.

Swap *activation* is not exercised: it requires root, a CONFIG_SWAP kernel
and mutates global system state.  See test_swapspace.sh for the rationale.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SwapspaceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    @property
    def swappath(self):
        return os.path.join(self.build_folder, "swapdir")

    @property
    def confdir(self):
        return os.path.join(self.build_folder, "confs")

    def build(self):
        os.makedirs(self.swappath, exist_ok=True)

        # Written into the build folder, never the source tree: the recipe
        # folder is the CI-read source of truth and must stay free of
        # generated files (CI JC4 junk check).
        confs = self.confdir
        os.makedirs(confs, exist_ok=True)

        with open(os.path.join(confs, "swapspace-test.conf"), "w",
                  encoding="utf-8") as f:
            f.write(f'swappath="{self.swappath}"\n')
            f.write("lower_freelimit=20\n")
            f.write("upper_freelimit=60\n")
            f.write("freetarget=30\n")
            f.write("cooldown=5\n")

        # A second directory with its own config file. Probing *this* one
        # proves the swappath is read from the config rather than from the
        # compiled-in default or from the -s flag.
        alt_swappath = os.path.join(self.build_folder, "swapdir-alt")
        os.makedirs(alt_swappath, exist_ok=True)
        with open(os.path.join(confs, "alt.conf"), "w", encoding="utf-8") as f:
            f.write(f'swappath="{alt_swappath}"\n')

        with open(os.path.join(confs, "relative.conf"), "w",
                  encoding="utf-8") as f:
            f.write('swappath="relative/dir"\n')

        with open(os.path.join(confs, "unknown.conf"), "w",
                  encoding="utf-8") as f:
            f.write("swapdir='/tmp'\n")

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["swapspace"]
        bin_path = os.path.join(dep.cpp_info.bindirs[0], "swapspace")
        script = os.path.join(self.source_folder, "test_swapspace.sh")
        confs = self.confdir
        self.run(
            f'sh "{script}" "{bin_path}" "{self.swappath}" "{confs}"',
            env="conanrun",
        )
