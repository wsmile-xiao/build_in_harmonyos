"""Conan test_package for ispell 3.4.06.
R34: Must actually exercise the tested binary.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IspellTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skipping execution test.")
            return

        dep = self.dependencies["ispell"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        test_dir = os.path.dirname(os.path.abspath(__file__))

        # ispell hardcodes LIBDIR=/usr/local/lib at compile time; the recipe
        # installs english.hash at <package_folder>/usr/local/lib (the conan
        # cache default BINDIR the upstream Makefile config.sh falls back to).
        # ispell reads the dictionary directory from env var ISPELL_DICTDIR
        # (config.X #define LIBRARYVAR "ISPELL_DICTDIR"), not LIBDIR — point
        # it at the package-relative path so `ispell -a` finds the dictionary
        # without writing to the real-machine root filesystem.
        # conan self.run's `env` only accepts predefined scope names, so inline
        # ISPELL_DICTDIR via the `env` command as a prefix.
        lib_dir = os.path.join(dep.package_folder, "usr", "local", "lib")
        self.run(
            f'env ISPELL_DICTDIR="{lib_dir}" zsh "{test_dir}/test_ispell.sh" "{bin_dir}"',
            env="conanrun",
        )
