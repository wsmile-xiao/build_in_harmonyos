import os
from conan import ConanFile


class PacaptTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["pacapt"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: real smoke test — exercises the packaged artifact by invoking
        # pacapt as a consumer would, verifying actual runtime behaviour.
        self.run(f"bash test_pacapt.sh {bin_dir}", env="conanrun")
        self.output.info("pacapt: OK")
