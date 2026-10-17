#!/usr/bin/env python3
"""Conan test_package — rblcheck 20231210 consumer verification.

Exercises the packaged CLI from a consumer's point of view (version, usage,
zone-list clear/toggle/list, and one real resolver query against the reserved
`.invalid` TLD so no external service is involved).

This is CONSUMER verification only.  The three upstream automake tests are run
by the recipe's build() step via `make check` and are NOT counted here.
"""
import os
import shutil

from conan import ConanFile


class RblcheckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_rblcheck.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
