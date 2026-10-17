#!/usr/bin/env python3
"""Conan test_package for kerberos-configs 2.7.

Real (non-stub) verification for a pure config package (R34): checks that the
installed krb5.conf template exists under share/kerberos-configs/ and that its
content is a well-formed krb5.conf — INI section headers present
([libdefaults]/[realms]/[domain_realm]), balanced realm braces, and key/value
assignments — using only POSIX sh builtins + grep/wc (adduser #17506 lesson:
no python3/perl invocation on OHOS CI workers; plain shell is the most robust).
"""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class KerberosConfigsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Pure config package: nothing to compile. test_kerberos_configs.sh is
        # the L0c test source (shell script, runs under CONFIG_SHELL/bash).
        pass

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_kerberos_configs.sh")
        self.run(f'"{bash}" "{script}" "{pkg}"', env="conanrun")
