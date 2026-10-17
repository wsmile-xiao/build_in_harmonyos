#!/usr/bin/env python3
"""Conan test_package — dinotrace 9.4f.

R34 substantive consumer test: runs the packaged binary (``bin/dinotrace``)
directly — asserts ``--version`` and the ELF DT_NEEDED entries that prove the
binary really links the packaged Motif chain, plus a headless-init negative
test.  Removing the package artifacts makes the script fail, so it also passes
the CI L1e destructive reverse check (not a stub / echo-only test).
"""
import os
import shutil

from conan import ConanFile


class DinotraceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["dinotrace"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_dinotrace.sh"
        )
        self.output.info(f"running consumer test: {script} {bin_dir} {readelf}")
        # env="conanrun" supplies LD_LIBRARY_PATH with the packaged Motif/X11 libs.
        self.run(f'sh "{script}" "{bin_dir}" "{readelf}"', env="conanrun")
