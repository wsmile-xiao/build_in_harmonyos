import os

from conan import ConanFile


class PixdTestConan(ConanFile):
    """test_package for the pixd executable — runs test_pixd.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_pixd.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution. stdin detached (`</dev/null`) —
        # same on-device exec restriction as the build toolchain (see notes).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_pixd.sh < /dev/null", env="conanrun")
