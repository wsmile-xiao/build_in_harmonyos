import os

from conan import ConanFile


class AcpidTestConan(ConanFile):
    """test_package for acpid 2.0.34 — executable verification.

    acpid is a daemon, not a library, so there is no API to link
    against.  Instead we verify both installed binaries:
      - acpid --version        (daemon, prints version, exits 0)
      - acpi_listen --help     (listener utility, prints usage)
    """
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
