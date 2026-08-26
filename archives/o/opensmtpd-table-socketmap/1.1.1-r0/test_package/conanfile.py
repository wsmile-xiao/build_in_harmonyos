import os

from conan import ConanFile


class OpensmtpdTableSocketmapTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the binary path from the installed package
        dep = self.dependencies["opensmtpd-table-socketmap"]
        bin_path = os.path.join(dep.package_folder, "bin", "table-socketmap")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{bin_path}"', env="conanrun")
