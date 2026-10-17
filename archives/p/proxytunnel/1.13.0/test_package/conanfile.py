import os

from conan import ConanFile


class ProxytunnelTestConan(ConanFile):
    """test_package for proxytunnel — runs test.sh which exercises the real
    binary: version banner, --help, a genuine CONNECT tunnel round-trip
    through a local mock proxy (request format + bidirectional data
    forwarding), the SSL_connect failure path (-e proves libssl is really
    linked) and the connection-refused error path."""
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
