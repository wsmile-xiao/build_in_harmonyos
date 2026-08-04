import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class YkushControlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ykush-control"]
        exe = os.path.join(dep.package_folder, "bin", "ykushcmd")
        assert os.path.isfile(exe), f"missing packaged executable: {exe}"
        if not can_run(self):
            self.output.info("Cross-build context: packaged ykushcmd verified; runtime test skipped")
            return
        self.run(f'"{sys.executable}" test_ykush_control.py "{exe}"', env="conanrun")
