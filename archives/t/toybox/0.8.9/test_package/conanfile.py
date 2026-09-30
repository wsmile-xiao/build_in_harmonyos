#!/usr/bin/env python3
"""Consumer test for the packaged toybox multi-call binary."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class ToyboxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "smoke.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("skipped: cannot execute target binaries here")
            return
        package_folder = self.dependencies["toybox"].package_folder
        toybox = os.path.join(package_folder, "bin", "toybox")
        if not os.path.isfile(toybox):
            raise Exception("packaged toybox binary missing: %s" % toybox)
        script = os.path.join(self.source_folder, "smoke.sh")
        self.run("sh %s %s" % (shlex.quote(script), shlex.quote(toybox)),
                 env="conanrun")
