#!/usr/bin/env python3
"""test_package for proftmb 1.1.12 executable — runs test.sh.

Consumer verification: invoke the installed binary the way a real OHOS user
would. Upstream proftmb 1.1.12 has no automated test suite; test.sh drives
three named HarmonyOS consumer cases (HC-1 --version, HC-2 full prediction on
the upstream example PSSM, HC-3 byte-for-byte output comparison against the
upstream reference outputs).

OHOS notes:
  * The installed binary is self-signed in package() (binary-sign-tool, E077)
    so HMDFS allows direct execve.
  * OHOS musl loader does not follow symlinks for DT_NEEDED (E050); package()
    flattens libgsl.so.28/libgslcblas.so.0 entity copies into <pkg>/lib and the
    binary carries RUNPATH $ORIGIN/../lib.
"""
import os

from conan import ConanFile


class ProftmbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use the sandbox bash to drive test.sh: /system/bin/sh (toybox) is
        # not a guaranteed ELF-exec wrapper on all OHOS workers (2048.c
        # precedent); hnp bash is always present on CI workers.
        # NOTE: no layout() here — cwd must stay on the test_package source
        # folder so the relative `test.sh` path resolves (2048.c pattern).
        bash = "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = os.environ.get("CONFIG_SHELL", "/system/bin/sh")
        self.run(f'"{bash}" test.sh', env="conanrun")
