#!/usr/bin/env python3
"""test_package for the jshon executable — runs the installed binary as a consumer.

Verifies that a consumer can invoke the packaged ``jshon`` binary end to end:
object/array traversal, every JSON value type (string/number/bool/null),
JSON creation and modification, invalid-input error paths, plus a dedicated
ELF section (ELF64/AArch64/PIE/musl interpreter/no host RPATH).
"""
import os

from conan import ConanFile


class JshonTestConan(ConanFile):
    """test_package for jshon executable — runs test.sh against the installed binary."""
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
