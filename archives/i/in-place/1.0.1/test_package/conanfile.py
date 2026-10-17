from conan import ConanFile


class InPlaceTestConan(ConanFile):
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("python3 consumer.py", env="conanrun")
