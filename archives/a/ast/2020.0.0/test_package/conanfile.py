import os

from conan import ConanFile


class AstTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must execute the ksh binary from the built package
        ksh_bin = os.path.join(self.dependencies["ast"].package_folder, "bin", "ksh")

        # Run the functional test script using ksh
        test_script = os.path.join(self.source_folder, "test_ksh.sh")
        self.run(f'"{ksh_bin}" "{test_script}"', env="conanrun")
