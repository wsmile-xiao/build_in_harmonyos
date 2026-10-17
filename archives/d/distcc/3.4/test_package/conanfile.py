from conan import ConanFile


class DistccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanrun env puts the package's bin/ on PATH, so `distcc` resolves.
        self.run("distcc --version", env="conanrun")
