import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["tsl-sparse-map"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_tsl_sparse_map.py")
            self.run(f'python3 "{test_script}" "{pkg}"', env="conanrun")