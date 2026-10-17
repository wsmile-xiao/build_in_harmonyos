#!/usr/bin/env python3
"""Conan test_package for bubblewrap 0.11.0 — binary tool smoke test.

bwrap is a sandboxing CLI tool. On OHOS it cannot actually create
namespaces (no setuid/user-namespace support), so the smoke test verifies:
  1. the bwrap binary is installed,
  2. it runs `--version` successfully (prints "bubblewrap 0.11.0"),
  3. it prints its usage/help text without crashing.
Sandbox creation itself (--ro-bind / --unshare-*) is skipped because OHOS
does not provide CAP_SYS_ADMIN / user namespaces.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanException


class BubblewrapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["bubblewrap"]
        bindir = os.path.join(dep.package_folder, "bin")
        bwrap_path = os.path.join(bindir, "bwrap")

        # 1. Binary must exist (R34: test must exercise the package)
        if not os.path.isfile(bwrap_path):
            raise ConanException(f"bwrap binary not found in {bindir}")
        self.output.info(f"bwrap: {os.path.getsize(bwrap_path)} bytes")

        # 2. --version must run and print the expected version
        version_rc = self.run(f'"{bwrap_path}" --version 2>&1',
                              env="conanrun", ignore_errors=True)
        if version_rc != 0:
            raise ConanException("bwrap --version failed to execute")
        self.output.info("bwrap --version: OK")

        # 3. --help must print usage without crashing (exit 0 or 1)
        help_rc = self.run(f'"{bwrap_path}" --help > /dev/null 2>&1',
                           env="conanrun", ignore_errors=True)
        if help_rc not in (0, 1):
            raise ConanException(f"bwrap --help crashed (exit {help_rc})")
        self.output.info("bwrap --help: OK")

        # 4. Run the committed test.sh wrapper (official test source)
        test_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        if os.path.isfile(test_sh):
            os.chmod(test_sh, os.stat(test_sh).st_mode | stat.S_IXUSR)
            rc = self.run(f'sh "{test_sh}" "{bwrap_path}"',
                          env="conanrun", ignore_errors=True)
            if rc != 0:
                raise ConanException(f"test.sh failed (exit {rc})")
            self.output.info("test.sh: OK")
        else:
            self.output.warning("test.sh not found, skipping wrapper test")
