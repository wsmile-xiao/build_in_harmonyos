import os

from conan import ConanFile


class WmrackTestConan(ConanFile):
    """test_package for the wmrack executable.

    wmrack is a GUI dock applet, so there is no library to link against: the
    consumer test exercises the installed binary instead (R34).  test.sh asserts
    the CLI contract, the dynamic dependency chain and the installed data files.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the script
        # itself is run through bash and executes the binary from inside bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
