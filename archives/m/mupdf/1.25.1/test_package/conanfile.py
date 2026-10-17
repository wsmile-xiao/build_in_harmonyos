#!/usr/bin/env python3
"""Test package for mupdf — verifies mutool binary works."""
import os

from conan import ConanFile
from conan.errors import ConanException


class MupdfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Resolve mutool by absolute path: the VirtualRunEnv generated
        # conanrun.sh carries no PATH entry for the dependency bindir on
        # OHOS (empty env script), so a bare "mutool" lookup fails with
        # exit 127 "inaccessible or not found" (E428).
        dep = self.dependencies["mupdf"]
        mutool = os.path.join(dep.package_folder, "bin", "mutool")
        if not os.path.isfile(mutool):
            raise ConanException(f"mutool not found: {mutool}")
        self.run(f'sh test.sh "{mutool}"', env="conanrun")
