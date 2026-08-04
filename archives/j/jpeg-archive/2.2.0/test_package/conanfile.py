"""Conan test_package for jpeg-archive 2.2.0.

R34: Must actually exercise the tested binaries.
jpeg-archive is a CLI tool set — test runs all 4 binaries with real input.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class JpegArchiveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skipping execution test.")
            return

        dep = self.dependencies["jpeg-archive"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        test_dir = os.path.dirname(os.path.abspath(__file__))

        self.run(
            f'sh "{test_dir}/test_jpeg_archive.sh" "{bin_dir}"',
            env="conanrun",
        )
