"""Independent Conan consumer for libGenome."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibgenomeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = Path(self.build_folder, self.cpp.build.bindirs[0], "test_libgenome")
        if not executable.is_file():
            raise ConanInvalidConfiguration("libgenome consumer executable missing")
        if not can_run(self):
            self.output.info("CONSUMER_RUNTIME=NOT_RUN: cross-built target executable")
            return
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            readelf = shutil.which("llvm-readelf")
            objcopy = shutil.which("llvm-objcopy")
            if not all((signer, readelf, objcopy)):
                raise ConanInvalidConfiguration("OHOS consumer requires signer, readelf and objcopy")
            pending = executable.with_name(executable.name + ".signing")
            signed = executable.with_name(executable.name + ".signed")
            if pending.exists() or signed.exists():
                raise ConanInvalidConfiguration("stale consumer signing sibling")
            try:
                shutil.copy2(executable, pending)
                sections = subprocess.run([readelf, "-S", str(pending)], capture_output=True, text=True, check=True, timeout=10).stdout
                if ".codesign" in sections:
                    subprocess.run([objcopy, "--remove-section", ".codesign", str(pending)], check=True, timeout=10)
                subprocess.run([signer, "sign", "-inFile", str(pending), "-outFile", str(signed), "-selfSign", "1"],
                               capture_output=True, check=True, timeout=40)
                sections = subprocess.run([readelf, "-S", str(signed)], capture_output=True, text=True, check=True, timeout=10).stdout
                if len(re.findall(r"\s\.codesign\s", sections)) != 1:
                    raise ConanInvalidConfiguration("consumer lacks a unique .codesign section")
                signed.chmod(executable.stat().st_mode | 0o755)
                os.replace(signed, executable)
            finally:
                for temporary in (pending, signed):
                    if temporary.exists():
                        temporary.unlink()
        self.run(str(executable), env="conanrun")
