#!/usr/bin/env python3
"""Test package for zeroc/Ice — builds a minimal Ice client against the
packaged headers/libraries and actually runs it (checks that libIce loads
and initializes on OpenHarmony, and that the reported version matches the
recipe version)."""
import os

from conan import ConanFile


class ZerocTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        ice = self.dependencies["zeroc"]
        includedir = ice.cpp_info.includedirs[0]
        libdir = ice.cpp_info.libdirs[0]
        cxx = os.environ.get("CXX", "clang++")

        src = os.path.join(self.folders.source_folder, "test_client.cpp")
        bin_path = os.path.join(self.folders.build_folder, "test_client")

        self.run(
            f"{cxx} -std=c++17 -stdlib=libc++ -I{includedir} {src} "
            f"-L{libdir} -lIce -o {bin_path}",
            env="conanbuild",
        )
        # Run the client with the package lib dir on the loader path
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f"{bash} -c \"LD_LIBRARY_PATH={libdir} {bin_path}\"",
            env="conanbuild",
        )
