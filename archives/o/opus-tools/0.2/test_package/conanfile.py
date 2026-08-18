#!/usr/bin/env python3
"""Installed-package consumer for opus-tools 0.2."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class OpusToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _ohos_tool(name):
        path = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
        if not os.path.isfile(path):
            raise ConanException(f"Required OHOS tool is missing: {name}")
        return path

    def _sign_ohos_elf(self, path):
        readelf = self._ohos_tool("llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        codesign_count = sections.count(".codesign")
        if codesign_count == 1:
            self.output.info(f"Preserving existing .codesign section: {path}")
            return
        if codesign_count != 0:
            raise ConanException(f"Consumer has invalid .codesign count: {codesign_count}")
        clean = path + ".codesign-clean"
        signed = path + ".opus-tools-test-signed"
        for generated in (clean, signed):
            if os.path.exists(generated):
                os.remove(generated)
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True,
                timeout=30,
            )
            subprocess.run(
                [signer, "sign", "-inFile", clean, "-outFile", signed, "-selfSign", "1"],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("Signed consumer has invalid .codesign count")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN: target execution is unavailable while cross-building")
            return
        bin_dir = os.path.join(self.dependencies["opus-tools"].package_folder, "bin")
        for name in ("opusenc", "opusdec", "opusinfo"):
            path = os.path.join(bin_dir, name)
            if not os.path.isfile(path):
                raise ConanException(f"Expected executable not found: {path}")
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(path)
        # Run version/help checks (opusinfo doesn't support --version)
        for name in ("opusenc", "opusdec"):
            path = os.path.join(bin_dir, name)
            self.run(f'"{path}" --version', env="conanrun")
        opusinfo_path = os.path.join(bin_dir, "opusinfo")
        self.run(f'"{opusinfo_path}" -h', env="conanrun")
        # Run functional test
        script = os.path.join(self.source_folder, "test_opus_tools.sh")
        self.run(f'sh "{script}" "{bin_dir}"', env="conanrun", cwd=self.build_folder)
