import os
from conan import ConanFile


class AbcdeTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["abcde"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact with the real smoke test
        # script (presence + executable bit + shebang + bash syntax check).
        self.run(f"bash test_abcde.sh {bin_dir}", env="conanrun")
        self.output.info("abcde: OK")
