#!/usr/bin/env python3
"""Conan test_package for ypserv 4.2 — consumer side verification.

`test.sh` runs inside the `conanrun` environment (the packaged sbin/ and
lib/yp/ directories are on PATH) and checks:

  * all nine packaged tools start and identify themselves as version 4.2,
  * the HarmonyOS specific password database compatibility layer really works
    (yphelper merges /etc/passwd+shadow and group+gshadow through the
    fgetpwent/fgetspent/fgetgrent implementations that musl libc does not
    provide — a stub would let the passwd field through instead of the hash),
  * makedbm writes and reads back a gdbm backed map (static gdbm/1.23, no
    libgdbm.so at run time).
"""
import os

from conan import ConanFile


class YpservTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # On OHOS /system/bin/sh is mksh, which cannot exec ELF binaries;
        # run the script through bash.
        bash = "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = "bash"
        self.run(f'"{bash}" test.sh', env="conanrun")
