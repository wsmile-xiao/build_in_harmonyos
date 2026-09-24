import os

from conan import ConanFile


class LibimobiledeviceProgsTestConan(ConanFile):
    """test_package for libimobiledevice-progs — runs test.sh which invokes the tools."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
