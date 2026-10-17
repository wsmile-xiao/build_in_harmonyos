#!/usr/bin/env python3
"""Conan test_package — twclock 3.5.

R34 substantive consumer test: runs the packaged binary (``bin/twclock``)
directly — asserts the ELF DT_NEEDED entries that prove the binary really
links the packaged Motif/X11/PulseAudio chain, the app-defaults resource
file, and a headless-init negative test.  Removing the package artifacts
makes the script fail, so it also passes the CI L1e destructive reverse
check (not a stub / echo-only test).
"""
import os
import shutil

from conan import ConanFile


class TwclockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["twclock"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_twclock.sh"
        )
        self.output.info(f"running consumer test: {script} {bin_dir} {readelf}")
        # env="conanrun" supplies LD_LIBRARY_PATH with the packaged Motif/X11/PulseAudio libs.
        self.run(f'sh "{script}" "{bin_dir}" "{readelf}"', env="conanrun")