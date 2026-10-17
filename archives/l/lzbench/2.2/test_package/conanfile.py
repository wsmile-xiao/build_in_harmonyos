import os
from conan import ConanFile


class LzbenchTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: exercise the packaged artifact — run lzbench smoke test
        bin_dir = os.path.join(self.dependencies["lzbench"].package_folder, "bin")
        self.run(f"bash test_lzbench.sh {bin_dir}", env="conanrun")
        self.output.info("lzbench: OK")
