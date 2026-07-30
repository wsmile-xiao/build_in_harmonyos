#!/usr/bin/env python3
"""Conan recipe for bpm-tools 0.3 — BPM (Beats Per Minute) audio analysis tool.

bpm-tools is a command-line tool that analyses the tempo of raw audio
on stdin (44100Hz, mono, 32-bit float) and outputs the detected BPM value.

Build system: simple Makefile (no configure script).
The Makefile respects CFLAGS (?= and +=), CC, and LDLIBS from the environment.
License: GPL-2.0
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class BpmtoolsConan(ConanFile):
    name = "bpm-tools"
    version = "0.3"
    description = "Audio BPM (Beats Per Minute) analysis tool"
    license = "GPL-2.0"
    homepage = "https://www.pogo.org.uk/~mark/bpm-tools/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — bpm-tools' Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain generates CC, CFLAGS, LDFLAGS etc. from Conan settings.
        # R33: All flags come from Conan toolchain, no shell env vars in build()
        # Used purely for conanbuildenv generation, not for autotools configure.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Simple Makefile project: make bpm from bpm.c, links libm
        # Use -j1 to avoid race conditions in simple Makefile builds
        # R33: CC, CFLAGS come from Conan toolchain (conanbuildenv)
        self.run("make -j1")

    def package(self):
        # Copy the bpm binary and shell scripts
        copy(self, "bpm", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bpm-graph", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bpm-tag", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # Sign ELF binary (HarmonyOS requires ELF signature for execution)
        bin_path = os.path.join(self.package_folder, "bin", "bpm")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            # Remove old signature if present (may fail if no .codesign section exists on fresh binary — expected)
            subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                           capture_output=True, timeout=10)
            # Sign with self-signed certificate
            tmp = bin_path + ".signed.tmp"
            for _attempt in range(3):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path,
                     "-outFile", tmp, "-selfSign", "1"],
                    capture_output=True, timeout=30)
                if r.returncode == 0 and os.path.exists(tmp):
                    shutil.move(tmp, bin_path)
                    break
                time.sleep(1)
            else:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise ConanException(
                    f"ELF signing failed after 3 attempts for {bin_path}. "
                    f"Binary will not be executable on HarmonyOS."
                )
            os.chmod(bin_path, 0o755)

    def package_info(self):
        # bpm-tools is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # bpm links against libm (system math library)
        self.cpp_info.system_libs = ["m"]
