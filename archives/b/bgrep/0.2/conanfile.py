#!/usr/bin/env python3
"""Conan recipe for bgrep 0.2 — binary grep tool.

bgrep searches for binary/hex patterns in files. It supports:
- Hex pattern search (e.g., `deadbeef`)
- Wildcard search (`??` matches any byte)
- Standard input and directory recursive search

Build system: simple Makefile (only `all: bgrep`, no configure script).
License: BSD
"""
import os
import subprocess
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class BgrepConan(ConanFile):
    name = "bgrep"
    version = "0.2"
    description = "Binary grep — search for binary/hex patterns in files"
    license = "BSD"
    homepage = "https://github.com/tmbinc/bgrep"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self.run("make -j1")

    def package(self):
        copy(self, "bgrep", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

        # Sign ELF binary (HarmonyOS requires ELF signature for execution)
        bin_path = os.path.join(self.package_folder, "bin", "bgrep")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            # Remove any existing .codesign section (may not exist on fresh build)
            r = subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                               capture_output=True, timeout=10)
            if r.returncode != 0:
                # Non-zero is expected if .codesign section doesn't exist yet
                pass
            tmp = bin_path + ".signed.tmp"
            for _attempt in range(3):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path,
                     "-outFile", tmp, "-selfSign", "1"],
                    capture_output=True, timeout=30)
                if r.returncode == 0 and os.path.exists(tmp):
                    shutil.move(tmp, bin_path)
                    break
                import time; time.sleep(1)
            else:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise ConanException(
                    f"ELF signing failed after 3 attempts for {bin_path}. "
                    f"Binary will not be executable on HarmonyOS."
                )
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
