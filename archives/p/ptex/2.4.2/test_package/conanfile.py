"""Installed Ptex shared-library consumer."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class PtexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
            if not signer or not readelf:
                raise ConanInvalidConfiguration("OHOS signer/readelf missing")
            binary = Path(self.build_folder, "ptex_consumer")
            signed = binary.with_name(binary.name + ".signed")
            if signed.exists():
                raise ConanInvalidConfiguration("stale signed consumer")
            try:
                subprocess.run([signer, "sign", "-inFile", str(binary),
                                "-outFile", str(signed), "-selfSign", "1"],
                               check=True, capture_output=True, text=True, timeout=40)
                sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                          capture_output=True, text=True, timeout=20)
                if ".codesign" not in sections.stdout:
                    raise ConanException("signed consumer lacks .codesign")
                os.chmod(signed, binary.stat().st_mode)
                os.replace(signed, binary)
            finally:
                if signed.exists():
                    signed.unlink()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "ptex_consumer"), env="conanrun")
