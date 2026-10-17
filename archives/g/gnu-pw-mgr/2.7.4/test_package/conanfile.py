from conan import ConanFile
import os


class GnuPwMgrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # gnu-pw-mgr is an application; the consumer test runs the installed
        # binaries and asserts real behaviour (bc/units precedent).
        self.run("bash test.sh", env="conanrun")
