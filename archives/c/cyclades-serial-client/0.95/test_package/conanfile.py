from conan import ConanFile
import os

class T(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run("sh \"%s\"" % script, env="conanrun")
