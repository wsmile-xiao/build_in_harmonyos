import os

from conan import ConanFile


class Abcm2psTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{config_shell} test.sh", env="conanrun")
