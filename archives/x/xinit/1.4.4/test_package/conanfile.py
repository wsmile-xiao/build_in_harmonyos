#!/usr/bin/env python3
"""Conan test_package - xinit 1.4.4."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class XinitTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["xinit"]
        xinit_bin = os.path.join(dep.package_folder, "bin", "xinit")
        startx_bin = os.path.join(dep.package_folder, "bin", "startx")
        if not can_run(self):
            for path in (xinit_bin, startx_bin):
                if not os.path.isfile(path):
                    raise Exception(f"Missing packaged file: {path}")
            self.output.info("Cross-building; file layout check completed")
            return

        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "check_xinit.sh")
        self.run(
            f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(xinit_bin)} {shlex.quote(startx_bin)}",
            env="conanrun",
        )
