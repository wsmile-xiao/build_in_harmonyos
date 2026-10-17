import os

from conan import ConanFile


class EximTestConan(ConanFile):
    """test_package for exim — runs the built exim MTA binary (R34).

    Invokes test.sh which runs `exim -bV` (print compiled-in configuration /
    version banner) and `exim --version`, asserting the binary is a functional
    exim 4.99.5 build with the expected features (OpenSSL TLS, Berkeley DB,
    DANE, DKIM).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
