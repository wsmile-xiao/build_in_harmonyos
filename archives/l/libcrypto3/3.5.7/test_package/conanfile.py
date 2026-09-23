#!/usr/bin/env python3
"""Conan test_package for libcrypto3 3.5.7 — Conan L1 official test.

Verifies that libcrypto3 provides a functional libcrypto library.
Only links against -lcrypto (not -lssl), since libcrypto3 exports only crypto.
"""
import os

from conan import ConanFile


class Libcrypto3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against libcrypto3 from Conan package
        dep = self.dependencies["libcrypto3"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        sys_flags = " ".join(f"-l{l}" for l in cpp.system_libs)
        # R49: test_package compilation also needs LD_LIBRARY_PATH for lld libxml2
        cc = os.environ.get("CC", "clang")
        ld_env = (
            "LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            ":/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/sysroot/usr/lib"
            ":${LD_LIBRARY_PATH:-}"
        )
        self.run(f"{ld_env} {cc} test_libcrypto.c -o test_libcrypto {inc_flags} {lib_flags} {link_flags} {sys_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
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
            self.run(f"{bash} -c './test_libcrypto'", env="conanrun")
        else:
            self.run("./test_libcrypto", env="conanrun")
