import os

from conan import ConanFile


class WmmiscTestConan(ConanFile):
    """test_package for wmmisc — runs test.sh which exercises the installed
    binary as an OHOS consumer (PF3/L0c: real self.run execution logic)."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
