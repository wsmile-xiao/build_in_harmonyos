#!/usr/bin/env python3
"""Conan test_package for openssl 3.5.6 — Conan L1 official test.

Uses direct compilation to verify OpenSSL library is functional.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class OpensslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against openssl from Conan package
        dep = self.dependencies["openssl"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        sys_flags = " ".join(f"-l{l}" for l in cpp.system_libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_openssl.c -o test_openssl {inc_flags} {lib_flags} {link_flags} {sys_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. Try CONFIG_SHELL first,
        # then fall back to common bash locations.
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.exists(bash):
            bash = ""
            for candidate in ["/data/service/hnp/bin/bash",
                              "/storage/Users/currentUser/usr/local/bin/bash",
                              "/usr/bin/bash", "/bin/bash"]:
                if os.path.exists(candidate):
                    bash = candidate
                    break
        if bash:
            self.run(f"{bash} -c './test_openssl'", env="conanrun")
        else:
            self.run("./test_openssl", env="conanrun")
