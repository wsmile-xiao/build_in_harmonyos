import os

from conan import ConanFile


class RiesTestConan(ConanFile):
    """test_package for the ries executable — runs test.sh, which invokes the
    installed `ries` binary the way a consumer would."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so run the
        # script with the bash that comes from the toolchain environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
