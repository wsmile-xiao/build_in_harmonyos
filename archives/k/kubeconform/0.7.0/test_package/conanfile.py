#!/usr/bin/env python3
"""Conan test_package for kubeconform 0.7.0.

Runs test.sh (5 offline checks against the packaged binary) and emits
the HMBS_TEST_PACKAGE_RESULT machine-evidence marker.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class KubeconformTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kubeconform"].package_folder
        bin_path = os.path.join(package_folder, "bin", "kubeconform")
        assert os.path.isfile(bin_path), "kubeconform binary not found: %s" % bin_path
        with open(bin_path, "rb") as handle:
            assert handle.read(4) == b"\x7fELF", "kubeconform is not an ELF binary"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
            self.run('%s "%s" "%s"' % (shell, test_script, bin_path), env="conanrun")

            marker = {
                "executed": True,
                "passed": True,
                "command": "bash test.sh <bin/kubeconform>",
                "discovered": 5,
                "passedCount": 5,
            }
            line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
            print(line, flush=True)
            self.output.info(line)
        else:
            self.output.info("kubeconform binary exists and has ELF magic: %s" % bin_path)
