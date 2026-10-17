import os

from conan import ConanFile


class KustomizerTestConan(ConanFile):
    """test_package for the kustomizer executable package.

    Delegates to test.sh, which actually runs the binary (--version, --help
    and an offline `build inventory`) instead of a print-only stub (R34/R9).
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries directly;
        # wrap the real execution in bash (CONFIG_SHELL override allowed).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
