#!/usr/bin/env python3
"""Conan test_package for arpoison 0.6 — command-line tool test.

arpoison is a command-line tool (not a library).
R34: Test executes the arpoison binary to verify it's properly built.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class ArpoisonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # lld from OHOS SDK requires libxml2.so.16 (missing); use GNU ld instead
        if str(self.settings.os) == "OHOS":
            tc.extra_exelinkflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_executable(self, exe):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", exe], check=True)
        subprocess.run([signer, "sign", "-inFile", exe, "-outFile", exe, "-selfSign", "1"], check=True)
        os.chmod(exe, 0o755)

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        if str(self.settings.os) == "OHOS":
            # Sign arpoison binary from the package so system() can execute it
            dep = self.dependencies["arpoison"]
            arpoison_bin = os.path.join(dep.package_folder, "bin", "arpoison")
            self._sign_executable(arpoison_bin)

            bin_path = os.path.join(self.build_folder, "test_arpoison")
            self._sign_executable(bin_path)
        else:
            bin_path = os.path.join(self.build_folder, "test_arpoison")
        self.run(f'"{bin_path}"', env="conanrun")
        # R34: Verify arpoison binary is installed and accessible
        self.run("command -v arpoison", env="conanrun")
