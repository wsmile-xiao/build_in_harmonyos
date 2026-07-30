#!/usr/bin/env python3
"""test_package for identity4c — direct compile, avoids cmake transitive dep issues with openssl."""
import os
from conan import ConanFile


class Identity4cTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["identity4c"]
        openssl = self.dependencies["openssl"]
        libxml2 = self.dependencies["libxml2"]

        inc = " ".join([
            f"-I{p}" for p in dep.cpp_info.includedirs
        ] + [
            f"-I{openssl.package_folder}/include",
            f"-I{libxml2.package_folder}/include/libxml2",
        ])
        lib = " ".join([
            f"-L{openssl.package_folder}/lib",
            f"-L{libxml2.package_folder}/lib",
            f"{os.path.join(dep.package_folder, 'lib', 'libufpidentity.a')}",
            "-lssl", "-lcrypto", "-lxml2", "-lm",
        ])

        # R33: Get compiler from profile conf, not bare shell variables
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(f"{cc} test_identity4c.c -o test_probe {inc} {lib}")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('./test_probe', env="conanrun")
