import os

from conan import ConanFile


class TimidityTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the binary exists in the package
        bin_path = os.path.join(self.dependencies["timidity"].package_folder, "bin", "timidity")
        if not os.path.exists(bin_path):
            raise FileNotFoundError("timidity binary not found in package")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")
