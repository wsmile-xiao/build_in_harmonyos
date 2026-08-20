#!/usr/bin/env python3
"""test_package for authbind 2.2.0 — real smoke of the packaged binary.

Runs test_authbind.sh which:
  1. actually executes the packaged `authbind --help` and asserts exit code 0
     with "usage:" in stdout (L0c: real test source, no fake/echo-only tests);
  2. builds test_dlopen.c against the packaged libauthbind.so and dlopen()s it,
     asserting the "bind" interposition symbol resolves (libc/libdl closure).
Runs with env="conanrun" so runtime paths resolve.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import save


class AuthbindTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        bin_candidates = [
            os.path.join(pkg, d, "authbind") for d in (dep.cpp_info.bindirs or [])
        ]
        bin_candidates += [
            os.path.join(pkg, "bin", "authbind"),
            os.path.join(pkg, "storage", "Users", "currentUser", "usr", "local", "bin", "authbind"),
        ]
        binary = next((p for p in bin_candidates if os.path.isfile(p)), bin_candidates[0])
        lib_candidates = [
            os.path.join(pkg, d, "libauthbind.so.1.0")
            for d in (dep.cpp_info.libdirs or [])
        ]
        lib_candidates += [
            os.path.join(pkg, "lib", "authbind", "libauthbind.so.1.0"),
            os.path.join(pkg, "storage", "Users", "currentUser", "usr", "local", "lib", "authbind", "libauthbind.so.1.0"),
        ]
        libauthbind = next((p for p in lib_candidates if os.path.isfile(p)), lib_candidates[0])

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cc = os.environ.get("CC", "clang")
        self.run(
            f'AUTHBIND_BIN="{binary}" LIBAUTHBIND="{libauthbind}" CC="{cc}" '
            f'SRC_DIR="{self.source_folder}" {bash} test_authbind.sh',
            env="conanrun",
        )
