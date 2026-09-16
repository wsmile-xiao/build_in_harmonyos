import os

from conan import ConanFile


class PfdTestConan(ConanFile):
    """test_package for portable-file-dialogs — compiles and runs a consumer
    program that includes the header and calls its API (R34)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap compile+run.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies[self.tested_reference_str]
        inc = os.path.join(dep.package_folder, "include")
        self.run(f'PFD_INC="{inc}" {bash} test.sh', env="conanrun")
