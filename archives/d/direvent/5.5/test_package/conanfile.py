from conan import ConanFile
import os


class DireventTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # direvent is an application; the consumer test runs the installed
        # daemon and asserts real event-dispatch behaviour (bc/units precedent).
        self.run("bash test.sh", env="conanrun")
