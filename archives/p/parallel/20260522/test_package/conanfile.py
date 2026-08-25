#!/usr/bin/env python3
"""Consumer test for GNU Parallel concurrent job execution."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import get
from conan.tools.layout import basic_layout


class ParallelTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    _upstream_url = (
        "https://git.data.coop/api/v1/repos/tange/parallel/"
        "archive/20260522.tar.gz"
    )
    _upstream_sha256 = (
        "45863b673356bb524e068d122bfbe20fd7bafe5bb26f6519e931942926faade6"
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()
        get(
            self,
            url=self._upstream_url,
            sha256=self._upstream_sha256,
            destination=os.path.join(self.build_folder, "upstream_snapshot"),
            strip_root=True,
        )

    def test(self):
        if can_run(self):
            parallel = os.path.join(
                self.dependencies["parallel"].package_folder, "bin", "parallel"
            )
            package_folder = self.dependencies["parallel"].package_folder
            license_file = os.path.join(
                package_folder, "licenses", "GPL-3.0-or-later.txt"
            )
            if not os.path.isfile(license_file) or os.path.getsize(license_file) == 0:
                raise RuntimeError("packaged GPL-3.0-or-later license is missing")
            perl = os.path.join(
                self.dependencies["perl"].package_folder, "bin", "perl"
            )
            test_script = os.path.join(self.source_folder, "test_parallel.sh")
            self.run(
                f'zsh "{test_script}" "{parallel}" "{perl}"', env="conanrun"
            )
            upstream_test_script = os.path.join(
                self.source_folder, "test_upstream_all.sh"
            )
            upstream_root = os.path.join(
                self.build_folder, "upstream_snapshot"
            )
            upstream_results = os.path.join(
                self.build_folder, "upstream_test_results"
            )
            package_bin = os.path.join(package_folder, "bin")
            self.run(
                f'bash "{upstream_test_script}" "{package_bin}" '
                f'"{upstream_root}" "{perl}" "{upstream_results}"',
                env="conanrun",
            )
