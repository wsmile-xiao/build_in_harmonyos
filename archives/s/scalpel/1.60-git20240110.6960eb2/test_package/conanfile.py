#!/usr/bin/env python3
"""test_package for scalpel executable — runs the installed `scalpel` binary.

Consumer verification: invoke the installed binary the way a real user would —
check the version banner and run an end-to-end forensic carve (three HTML
blocks seeded into a small raw image, carved back out via a minimal config)
and verify the carved content byte-for-byte plus the audit log.
"""
import os
import tempfile

from conan import ConanFile


class ScalpelTestConan(ConanFile):
    """test_package for scalpel executable — runs test.sh which invokes the scalpel binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Run the carve in a scratch directory so the test never leaves
        # image/carve artifacts inside the (tracked) test_package source tree.
        test_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        work = tempfile.mkdtemp(prefix="scalpel-test-package-")
        self.run(f"{bash} {test_sh}", env="conanrun", cwd=work)
