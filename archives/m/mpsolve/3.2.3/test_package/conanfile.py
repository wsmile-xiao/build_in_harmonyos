import os

from conan import ConanFile


class MpsolveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["mpsolve"]
        bin_dir = os.path.join(pkg.package_folder, "bin", "mpsolve")
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "smoke_mpsolve.sh")}" "{bin_dir}"',
            env="conanrun",
        )
