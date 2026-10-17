import os

from conan import ConanFile


class AvidaTestConan(ConanFile):
    """test_package for avida/2.12.4 — digital evolution platform."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # avida is OHOS-only; skip on other platforms
        if self.settings.os != "OHOS":
            self.output.info("Skipping test: avida is OHOS-only")
            return

        bash = os.environ.get("CONFIG_SHELL", "bash")
        pkg_folder = self.dependencies["avida"].package_folder
        test_env = f"AVIDA_PACKAGE_DIR={pkg_folder}"
        self.run(f"{test_env} {bash} {self.source_folder}/test.sh", env="conanrun")
