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
            script = os.path.join(os.path.dirname(__file__), "test_interrogate.py")
            # The Conan sandbox PATH has no python3 — use an absolute path.
            py = "/data/service/hnp/bin/python3" if os.path.isfile(
                "/data/service/hnp/bin/python3"
            ) else sys.executable
            # The package folder is passed so the script can verify that what
            # it imported came from the packaged tree, and the dependency
            # folders travel as name=folder arguments so the script can
            # assert each import resolved from its own package folder — the
            # provenance check that distinguishes "the PYTHONPATH chain is
            # correct" from "a user-site copy happened to answer the import".
            pkg = self.dependencies["interrogate"].package_folder
            dep_args = " ".join(
                f'"{name}={self.dependencies[name].package_folder}"'
                for name in ("attrs", "click", "colorama", "tabulate")
            )
            # env="conanrun" carries the package's PYTHONPATH *and* PATH, so
            # the assertions see exactly what a consumer of this package
            # sees. PYTHONNOUSERSITE keeps the user site out of sys.path so
            # the two environments cannot disagree.
            self.run(
                f'PYTHONNOUSERSITE=1 {py} "{script}" "{pkg}" {dep_args}',
                env="conanrun",
            )
