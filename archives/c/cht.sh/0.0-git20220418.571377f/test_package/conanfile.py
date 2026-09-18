#!/usr/bin/env python3
"""Test package for cht.sh.

L1 checks (no network, no runtime deps — the --help branch exits before
rlwrap/mktemp checks):
1. bin/cht.sh installed and a non-empty file
2. bash -n syntax check passes
3. cht.sh --help exits 0 and prints Usage
4. the three shell completion files are installed
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ChtShTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["cht.sh"]
        pkg = str(dep.package_folder)
        script = os.path.join(pkg, "bin", "cht.sh")
        if not (os.path.isfile(script) and os.path.getsize(script) > 0):
            raise Exception(f"cht.sh script not found at {script}")
        self.output.info(f"cht.sh installed at {script}")

        # functional test (see test.sh)
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {test_sh}", env="conanrun")
