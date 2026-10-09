"""Exercise the installed qmc binary as a package consumer."""

import os

from conan import ConanFile


class QmcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = (os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
                 if self.settings.os == "OHOS" else "/bin/bash")
        self.run(f'"{shell}" test.sh', env="conanrun")
