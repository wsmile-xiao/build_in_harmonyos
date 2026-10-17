#!/usr/bin/env python3
"""Conan test_package — aescrypt-packetizer 3.16

Smoke test: verify the library can be linked against and the core API
(aes_context, sha256_context) is accessible.
"""
import os
from conan import ConanFile


class AescryptpacketizerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        inc_dir = self.dependencies["aescrypt-packetizer"].cpp_info.includedirs[0]
        lib_dir = self.dependencies["aescrypt-packetizer"].cpp_info.libdirs[0]
        src = os.path.join(self.source_folder, "test_smoke.c")
        self.run(
            f"{cc} -I{inc_dir} -L{lib_dir} {src} -lAESCryptPacketizer -o test_smoke",
            env="conanbuild",
        )

    def test(self):
        self.run("./test_smoke", env="conanrun")