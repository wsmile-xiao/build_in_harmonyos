import os

from conan import ConanFile


class OcservTestConan(ConanFile):
    """test_package for ocserv — executes the installed server binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: actually execute the packaged binaries. ocserv --version
        # prints the server banner (verified on device: "OpenConnect VPN
        # Server 1.5.0"); ocpasswd --version prints its own version.
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries —
        # use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
