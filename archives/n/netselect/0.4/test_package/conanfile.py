#!/usr/bin/env python3
"""test_package for netselect executable — exercises the installed binary.

netselect needs a raw ICMP socket (root/CAP_NET_RAW) to actually probe hosts,
which is not available in a normal build/test sandbox. The consumer test
therefore verifies the deterministic no-privilege, no-network code paths that
run BEFORE any socket is used: usage output and argv validation
(see netselect.c main(): getopt + "argc < 1" checks happen before the
socket_errno branch, so exit codes are stable without root).
"""
import os

from conan import ConanFile


class NetselectTestConan(ConanFile):
    """test_package for netselect executable — runs test.sh against the installed binary."""
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
