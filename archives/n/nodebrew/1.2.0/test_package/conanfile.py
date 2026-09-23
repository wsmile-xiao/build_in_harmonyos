#!/usr/bin/env python3
"""Conan test_package — nodebrew 1.2.0.

nodebrew is a pure perl script tool.  test() really executes the packaged
`bin/nodebrew` via a bash smoke script (R34: real execution, no print-only):
presence + executable bit + perl shebang + `perl -c` syntax check, then runs
`version`/`help` and asserts the output contains the expected "1.2.0".
"""
import os

from conan import ConanFile


class NodebrewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["nodebrew"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: real smoke test — actually execute the packaged perl script.
        self.run(f"bash test_nodebrew.sh {bin_dir}", env="conanrun")
        self.output.info("nodebrew: OK")
