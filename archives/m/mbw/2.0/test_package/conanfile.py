#!/usr/bin/env python3
"""Installed-package tests for mbw 2.0 (memory bandwidth benchmark).

Runs the packaged `mbw` executable on a tiny 8 MiB array with a single
iteration and asserts the benchmark produced a bandwidth result, which binds
the test to the actual built binary.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MbwTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_mbw.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("mbw target consumers are not runnable")
        binary = os.path.join(
            self.dependencies["mbw"].package_folder, "bin", "mbw"
        )
        if not os.path.isfile(binary):
            raise ConanException(f"packaged mbw binary missing: {binary}")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(binary)
        script = os.path.join(self.source_folder, "test_mbw.sh")
        self.run(f"sh {script} {binary} -n 1 -a 8", env="conanrun")

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
