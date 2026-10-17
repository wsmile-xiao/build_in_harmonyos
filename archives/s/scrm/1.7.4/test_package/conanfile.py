import os
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv


class ScrmTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not cross_building(self):
            executable = os.path.join(self.dependencies["scrm"].package_folder, "bin", "scrm")
            self.run('python3 "{}" "{}"'.format(os.path.join(self.source_folder, "test.py"), executable), env="conanrun")
