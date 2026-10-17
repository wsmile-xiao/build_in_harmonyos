import os
import shutil

from conan import ConanFile


class AxelTestConan(ConanFile):
    """test_package for axel — runs test.sh which invokes the axel binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(f"{bash} test.sh", env="conanrun")
