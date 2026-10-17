#!/usr/bin/env python3
"""Runtime test for the packaged chezdav 3.0 command-line server."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class ChezdavTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_chezdav.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info(
                "cross-building: packaged target executable cannot run on build host"
            )
            return

        package = self.dependencies["chezdav"]
        binary = os.path.join(package.package_folder, "bin", "chezdav")
        if not os.path.isfile(binary):
            raise ConanException("chezdav binary is missing: {}".format(binary))

        work = os.path.join(self.build_folder, "chezdav-runtime-test")
        os.makedirs(work, exist_ok=True)
        script = os.path.join(self.source_folder, "test_chezdav.sh")
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(
            '"{}" "{}" "{}" "{}"'.format(bash, script, binary, work),
            env="conanrun",
        )
