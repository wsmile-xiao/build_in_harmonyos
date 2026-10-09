#!/usr/bin/env python3
"""test_package for winregfs — exercises the installed console tools.

Consumer verification: run the packaged ``fsck.winregfs`` on a real (generated)
registry hive and check the traversal output, plus the ``mount.winregfs``
version banner and the corruption-reporting path. See test.sh.
"""
import os

from conan import ConanFile


class WinregfsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{bindir}"', env="conanrun")
