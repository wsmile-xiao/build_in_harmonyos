#!/usr/bin/env python3
"""Conan packaged-data and native/HDC consumer tests for PARI seadata-big."""

import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PariSeadataBigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.user_presets_path = False
        if self.settings.os == "OHOS":
            toolchain.cache_variables["OHOS_ARCH"] = {
                "armv8": "arm64-v8a", "x86_64": "x86_64", "armv7": "armeabi-v7a"
            }[str(self.settings.arch)]
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies["pari-seadate-big"]
        datadir = os.path.join(dependency.package_folder, "share", "pari")
        suffix = ".exe" if self.settings.os == "Windows" else ""
        consumer = os.path.abspath(os.path.join(
            self.build_folder, self.cpp.build.bindirs[0], "test_seadata" + suffix))
        command = [sys.executable, os.path.join(self.recipe_folder, "test_data.py"),
                   datadir, "--consumer", consumer]
        hdc = os.environ.get("PARI_SEADATA_HDC")
        if hdc:
            if self.settings.os != "OHOS":
                raise ConanException("HDC tests require an OHOS host profile")
            command.extend(["--hdc", hdc, "--target", os.environ.get("PARI_SEADATA_HDC_TARGET", "")])
        elif not can_run(self):
            raise ConanException("Cross tests require PARI_SEADATA_HDC; target tests cannot be skipped")
        elif self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            self.run(f'{shlex.quote(signer)} sign -inFile {shlex.quote(consumer)} '
                     f'-outFile {shlex.quote(consumer)} -selfSign 1', env="conanrun")
            command.append("--ohos")
        rendered = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
        self.run(rendered, env=None if hdc else "conanrun")
