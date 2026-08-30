#!/usr/bin/env python3
"""Conan test_package for cbftp 1.0.0 — standalone consumer test.

cbftp is a pure command-line tool package (bin/cbftp + bin/datafilecat +
bin/datafilewrite) with no public library API, so the consumer test runs the
packaged binaries directly (R34): real AES-256 data file encrypt/decrypt
round trips via datafilewrite/datafilecat, wrong-passphrase rejection, and
cbftp ELF startup.

The test script locates libc++_shared.so under the OHOS SDK llvm lib dir by
itself (the binaries link libc++_shared.so at runtime).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class CbftpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sdk_root(self):
        """Locate the OHOS SDK root dynamically (avoid hardcoding a version)."""
        env_root = os.environ.get("OHOS_SDK_LLVM_ROOT")
        if env_root:
            return env_root
        base = "/data/service/hnp/ohos-sdk.org"
        if os.path.isdir(base):
            for entry in sorted(os.listdir(base), reverse=True):
                llvm_lib = os.path.join(base, entry, "ohos", "native", "llvm", "lib")
                if os.path.isdir(llvm_lib):
                    return llvm_lib
        return base if os.path.isdir(base) else ""

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            bin_dir = os.path.join(
                self.dependencies["cbftp"].package_folder, "bin")
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_cbftp.py")
            # Root for the test script to recurse and find libc++_shared.so;
            # passing the llvm/lib dir directly, or the SDK root as fallback.
            llvm_lib = self._sdk_root()
            self.run(f'{python_exe} "{test_script}" "{bin_dir}" "{llvm_lib}"',
                     env="conanrun")