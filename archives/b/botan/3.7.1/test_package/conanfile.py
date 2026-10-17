#!/usr/bin/env python3
"""Conan test_package for botan 3.7.1 — consumer-perspective functional test.

Direct compilation (blake3-style) to keep the test portable: links against
libbotan-3.a from the Conan package and runs 4 real assertions
(version / SHA-256 KAT / HMAC KAT / RNG).

CI L0d requires self.run() in this file.
File location: archives/b/botan/3.7.1/test_package/conanfile.py
"""
import os

from conan import ConanFile


class BotanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against botan from Conan package
        dep = self.dependencies["botan"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        cxx = os.environ.get("CXX", "clang++")
        self.run(
            f"{cxx} -std=c++20 test.cpp -o test_botan {inc_flags} {lib_flags} {link_flags}"
        )

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. The test binary is an OHOS
        # aarch64 ELF and needs libc++_shared.so from the OHOS SDK —
        # same LD_LIBRARY_PATH chain as the CI profile buildenv.
        # Static paths only: conanrun env's LD_LIBRARY_PATH can contain
        # whitespace/newlines that break shell word-splitting.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        sdk_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                   "/ohos/native/llvm/lib/aarch64-linux-ohos")
        self.run(
            f"{bash} -c 'LD_LIBRARY_PATH={sdk_lib}:/system/lib64 ./test_botan'",
            env="conanrun",
        )
