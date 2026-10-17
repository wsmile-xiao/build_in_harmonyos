import os

from conan import ConanFile


class PowermanTestConan(ConanFile):
    """test_package for powerman 2.4.4 — R34 smoke suite (consumer perspective).

    Starts a real powermand on an uncommon high port with one coprocess
    "vpc" device (vpc-sim.sh: bash re-implementation of the upstream
    t/simulators/vpcd protocol subset), then drives it through the
    installed powerman client: version, node list, query, on, off,
    union/compression semantics, graceful shutdown.  A trap in test.sh
    reaps the daemon and coprocess even on failure.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute the test suite
        # reliably; wrap with bash (posh/aa3d/brender test_package
        # precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('"{}" test.sh'.format(bash), env="conanrun")
