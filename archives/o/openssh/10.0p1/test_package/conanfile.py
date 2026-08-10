import os

from conan import ConanFile


class OpensshTestConan(ConanFile):
    """test_package for openssh — verifies binaries are installed and are valid ELF."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["openssh"]
        pkg_folder = pkg.package_folder
        self.output.info(f"Package folder: {pkg_folder}")

        # Run verification script (L0c requires test source file in test_package/)
        test_script = os.path.join(self.recipe_folder, "test_verify.sh")
        self.run(f'/system/bin/sh "{test_script}" "{pkg_folder}"', env="conanrun")
