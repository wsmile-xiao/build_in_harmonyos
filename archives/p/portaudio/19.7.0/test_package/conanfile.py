#!/usr/bin/env python3
"""Conan test package for PortAudio 19.7.0."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PortaudioTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_portaudio")
            if self.settings.os == "OHOS":
                self._sign_ohos_elf(executable)
            upstream = os.path.join(self.dependencies["portaudio"].package_folder, "tests", "paqa_errs")
            if not os.path.isfile(upstream):
                raise ConanException("Missing packaged upstream test: paqa_errs")
            if self.settings.os == "OHOS":
                self._sign_ohos_elf(upstream)
            completed = subprocess.run(
                [upstream], check=True, capture_output=True, text=True, timeout=120
            )
            output = completed.stdout + completed.stderr
            self.output.info(output.strip())
            if not re.search(r"QA Report: [0-9]+ passed, 0 failed\.", output):
                raise ConanException("PortAudio paqa_errs did not report zero failures")
            self.run(executable, env="conanrun")

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing consumer executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".portaudio-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
