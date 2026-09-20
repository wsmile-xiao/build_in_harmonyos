import os

from conan import ConanFile


class Xf86VideoR128TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # X.Org driver modules are .so files loaded at runtime by the X
        # server; verify the packaged module exists, is a valid ELF
        # shared object and exports the module entry point.
        pkg_root = self.dependencies["xf86-video-r128"].package_folder
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'bash "{test_script}" "{pkg_root}"', env="conanrun")
