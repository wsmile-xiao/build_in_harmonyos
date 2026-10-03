#!/usr/bin/env python3
"""test_package for the sysrqd daemon — verifies the installed binary as a consumer.

Upstream has no test suite (no tests/, no make test/check target), so this
consumer test exercises the installed ``bin/sysrqd`` binary directly.

sysrqd takes no command-line arguments (``int main(void)``). Its startup path:
- non-root: prints "Only root can run this program." to stderr and exits 1
  (before daemonizing — safe to run);
- root without /etc/sysrqd.secret: syslog error + exit 1 (also pre-daemon).

Either way the process exits non-zero without hanging, so the assertions below
hold on both root and non-root test accounts. A timeout guard is added anyway
in case a root environment happens to provide the secret file.
"""
import os

from conan import ConanFile


class SysrqdTestConan(ConanFile):
    """test_package for sysrqd — runs test.sh against the installed binary."""
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
