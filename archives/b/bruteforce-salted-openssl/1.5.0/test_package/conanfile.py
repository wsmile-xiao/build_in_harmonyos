from conan import ConanFile
from conan.tools.build import can_run
import os


class BruteforceSaltedOpensslTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["bruteforce-salted-openssl"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "bruteforce-salted-openssl")
            assert os.path.isfile(cmd_path), f"bruteforce-salted-openssl not found at {cmd_path}"
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} test.sh", env="conanrun")
