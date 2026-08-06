#!/usr/bin/env python3
"""test_package for eot-utils — R34: exercises real binaries (mkeot, eotinfo).

Uses test_eot_utils.sh to run mkeot (TTF→EOT) and eotinfo (EOT header parse)
with a system font. Both must succeed.
"""
import os

from conan import ConanFile


class EotUtilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["eot-utils"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        # R34: run the test script that exercises mkeot and eotinfo
        self.run(f"bash test_eot_utils.sh {bin_dir} {self.build_folder}",
                 env="conanrun")
        self.output.info("eot-utils: mkeot + eotinfo functional test passed")
