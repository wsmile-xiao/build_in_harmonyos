#!/usr/bin/env python3
"""Conan test_package — imapfilter L1 test.

imapfilter is a standalone CLI application, so the consumer test executes
the packaged binary itself via test.sh (R34: real execution, not a print-only stub):
  1. `imapfilter -V` must exit 0 and print the version banner
     ("IMAPFilter 2.8.3 ...", stderr).
  2. `imapfilter -h` must exit 0 and print the usage line
     ("usage: imapfilter [-inVv] ...", stderr) — exercises option parsing.
  3. All 8 packaged Lua runtime modules must exist in share/imapfilter
     inside the package (the binary loads them from its compiled-in
     SHAREDIR before executing any Lua code).
"""
import os

from conan import ConanFile


class ImapfilterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the packaged share/imapfilter for the packaging-completeness
        # check performed by test.sh (step 3 there).
        dep = self.dependencies.get("imapfilter")
        share = os.path.join(dep.package_folder, "share", "imapfilter")
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution (repo-standard pattern).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{share}"', env="conanrun")
