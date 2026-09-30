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
            script = os.path.join(os.path.dirname(__file__), "test_pytest.py")
            # The Conan sandbox PATH has no python3 — use an absolute path.
            py = "/data/service/hnp/bin/python3" if os.path.isfile(
                "/data/service/hnp/bin/python3"
            ) else sys.executable
            # The package folder is passed so the script can verify that what it
            # imported and executed really came from the packaged tree. This
            # machine also has an importable pytest in the user site directory
            # plus a pytest program in the user bin directory, so without that
            # check the test would still pass with the package folder emptied —
            # which the CI destructive negative test does deliberately.
            pkg = self.dependencies["pytest"].package_folder
            # The runtime dependencies travel as name=folder arguments so the
            # script can assert each of them was imported from its own packaged
            # tree. That check is what distinguishes "the PYTHONPATH chain is
            # correct" from "a user-site copy happened to satisfy the import" —
            # the latter is exactly how an earlier revision passed here while
            # CI, running as a uid that cannot read the user site directory,
            # failed with "No module named 'pluggy'".
            dep_args = " ".join(
                f'"{name}={self.dependencies[name].package_folder}"'
                for name in ("pluggy", "iniconfig", "packaging", "pygments")
            )
            # env="conanrun" carries the package's PYTHONPATH *and* PATH, so the
            # assertions see exactly what a consumer of this package sees.
            #
            # PYTHONNOUSERSITE=1 keeps the user site out of sys.path so the two
            # environments cannot disagree.
            self.run(
                f'PYTHONNOUSERSITE=1 {py} "{script}" "{pkg}" {dep_args}',
                env="conanrun",
            )
