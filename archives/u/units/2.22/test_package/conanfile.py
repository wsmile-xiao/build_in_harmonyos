from conan import ConanFile
import os


class UnitsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # units is an application; the consumer test runs the installed
        # binary and asserts conversion behaviour (bc/1.07.1 precedent).
        pkg = self.dependencies[self.tested_reference_str].package_folder
        defs = os.path.join(pkg, "share", "units", "definitions.units")
        self.run(f'bash test.sh "{defs}"', env="conanrun")
