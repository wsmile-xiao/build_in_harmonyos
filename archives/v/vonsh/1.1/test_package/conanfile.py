import os

from conan import ConanFile


class VonshTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Headless smoke run: SDL dummy video/audio drivers let the game
        # initialize and enter its loop; timeout(1) kills it at 5s (exit 124).
        pkg = self.dependencies["vonsh"]
        bin_dir = os.path.join(pkg.package_folder, "bin", "vonsh")
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "smoke_vonsh.sh")}" "{bin_dir}"',
            env="conanrun",
        )
