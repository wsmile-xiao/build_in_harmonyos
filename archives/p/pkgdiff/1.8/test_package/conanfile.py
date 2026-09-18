from conan import ConanFile
import os

class TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run("sh \"%s\"" % script, env="conanrun")
