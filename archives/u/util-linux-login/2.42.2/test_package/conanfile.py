#!/usr/bin/env python3
"""L1 test for util-linux-login: verify login and nologin binaries were built."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class UtilLinuxLoginTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if can_run(self):
            pkg = self.dependencies["util-linux-login"]
            bindir = pkg.cpp_info.bindirs[0]
            login_bin = os.path.join(bindir, "login")
            nologin_bin = os.path.join(bindir, "nologin")
            # Compile test.c
            self.run(
                f"clang test.c -o test_util_linux_login",
                env="conanbuild",
            )
            # Store paths for test()
            self._login_bin = login_bin
            self._nologin_bin = nologin_bin

    def test(self):
        if can_run(self):
            pkg = self.dependencies["util-linux-login"]
            bindir = pkg.cpp_info.bindirs[0]
            login_bin = os.path.join(bindir, "login")
            nologin_bin = os.path.join(bindir, "nologin")
            # Run the compiled C test
            self.run(
                f"./test_util_linux_login {login_bin} {nologin_bin}",
                env="conanrun",
            )
            # Also try running login --help for additional verification
            self.run(f"{login_bin} --help", env="conanrun", ignore_errors=True)
            self.output.info("OK: login smoke test completed")
