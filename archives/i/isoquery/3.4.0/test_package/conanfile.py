#!/usr/bin/env python3
"""Consumer test for the packaged isoquery binary."""

import os
import shutil

from conan import ConanFile


class IsoqueryTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct require so the consumer can read the published JSON tree.
        # The tested recipe already requires the same reference.
        self.requires("iso-codes/4.20.1")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        package = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package, "bin", "isoquery")
        fixture = os.path.join(self.source_folder, "fixture")
        iso_root = self.dependencies["iso-codes"].package_folder
        json_dir = os.path.join(iso_root, "share", "iso-codes", "json")
        script = os.path.join(self.source_folder, "test_isoquery.sh")
        self.run(
            '"%s" "%s" "%s" "%s" "%s"' % (bash, script, binary, fixture, json_dir),
            env="conanrun",
        )
