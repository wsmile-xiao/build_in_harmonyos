import os

from conan import ConanFile


class MpdasTestConan(ConanFile):
    """test_package for the mpdas executable - runs test.sh against the installed binary."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
