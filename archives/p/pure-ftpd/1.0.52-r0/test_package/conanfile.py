from conan import ConanFile
class PureftpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def test(self):
        self.run("pure-ftpd --help", env="conanrun")
