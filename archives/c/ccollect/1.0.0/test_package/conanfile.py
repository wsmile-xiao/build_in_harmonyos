import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class CcollectTestConan(ConanFile):
    """test_package for ccollect executable — runs the real ccollect binary."""
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["ccollect"]
            bin_dir = os.path.join(dep.package_folder, "bin")

            sh_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("sh")
                or "/system/bin/sh"
            )

            self.run(
                f'cd "{self.source_folder}" && '
                f'CONFIG_SHELL="{sh_path}" '
                f'"{sh_path}" test.sh "{bin_dir}"',
                env="conanrun",
            )
