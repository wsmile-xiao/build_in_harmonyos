from conan import ConanFile
import os


class MicronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # micron ships applications (daemon + client); the consumer test runs
        # the installed binaries and asserts their real behaviour.
        self.run("bash test.sh", env="conanrun")
