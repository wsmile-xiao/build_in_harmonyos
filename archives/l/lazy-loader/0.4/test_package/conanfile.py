import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(os.path.dirname(__file__), "test_lazy_loader.py")
            # The Conan sandbox PATH has no python3 — use an absolute path.
            py = "/data/service/hnp/bin/python3" if os.path.isfile(
                "/data/service/hnp/bin/python3"
            ) else sys.executable
            # The package folder is passed so the script can verify that what
            # it imported came from the packaged tree. This machine also has
            # an importable lazy_loader in the user site directory, so without
            # that check the test would still pass with the package folder
            # emptied — which the CI destructive negative test does on
            # purpose.
            pkg = self.dependencies["lazy-loader"].package_folder
            # env="conanrun" carries the package's PYTHONPATH so the module
            # is imported from the package folder rather than the build
            # machine.
            self.run(f'{py} "{script}" "{pkg}"', env="conanrun")
