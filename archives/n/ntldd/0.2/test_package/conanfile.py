import os

from conan import ConanFile
from conan.tools.build import can_run


class NtlddTestConan(ConanFile):
    """Conan consumer test for package ntldd 0.2."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip runtime consumer test")
            return

        package = self.dependencies["ntldd"]
        binary = os.path.join(package.package_folder, "bin", "ntldd")
        if not os.path.isfile(binary):
            raise AssertionError(f"ntldd binary not found: {binary}")

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test_ntldd.sh")
        self.run(f'{bash} "{script}" "{binary}"', env="conanrun")
