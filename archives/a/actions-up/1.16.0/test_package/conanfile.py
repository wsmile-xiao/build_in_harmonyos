from conan import ConanFile


class ActionsUpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("/system/bin/sh test_actions_up.sh", env="conanrun")
