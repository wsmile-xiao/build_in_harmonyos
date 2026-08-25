#!/usr/bin/env python3
"""Conan recipe for spim 9.1.24 — MIPS32 simulator.

SPIM is a MIPS32 simulator that implements both a terminal interface.
Source is hosted on SourceForge SVN (official repository).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class SpimConan(ConanFile):
    name = "spim"
    version = "9.1.24"
    description = "MIPS32 simulator (MIPS R2000/R3000 assembly language simulator)"
    license = "BSD"
    homepage = "https://spimsimulator.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # SPIM source is hosted on SourceForge SVN (official repository).
        # The SVN revision 764 corresponds to version 9.1.24.
        # Download files from the SVN HTTP interface in parallel for speed.
        svn_base = self.conan_data["sources"]["url"]
        files = self.conan_data["sources"]["files"]
        src = self.source_folder
        # Create a download script that runs curl in parallel
        lines = ["#!/data/service/hnp/bin/bash"]
        for rel_path in files:
            url = f"{svn_base}/{rel_path}"
            dest = os.path.join(src, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            lines.append(f'curl -sL -o "{dest}" "{url}" &')
        lines.append("wait")
        script = os.path.join(src, "_download.sh")
        with open(script, "w") as f:
            f.write("\n".join(lines))
        os.chmod(script, 0o755)
        self.run(f"bash {script}")

    def build(self):
        # SPIM uses a Makefile in the spim/ subdirectory.
        # The Makefile references ../CPU/ for core source files.
        # Use GNU ld (ld.bfd) instead of lld to avoid libxml2.so.16 dependency issue.
        ld_bfd = shutil.which("ld.bfd") or "/data/service/hnp/bin/ld.bfd"
        build_dir = os.path.join(self.source_folder, "spim")
        self.run(f'make -C {build_dir} -j1 spim CXX=clang++ LDFLAGS="-lm -fuse-ld={ld_bfd}"')

        # Sign the ELF binary for HarmonyOS (required for execution)
        spim_bin = os.path.join(build_dir, "spim")
        self._sign_elf(spim_bin)

    def package(self):
        # Copy the spim binary
        spim_bin = os.path.join(self.source_folder, "spim", "spim")
        copy(self, "spim", os.path.dirname(spim_bin),
             os.path.join(self.package_folder, "bin"))

        # Re-sign after copy (copy may strip signature)
        pkg_bin = os.path.join(self.package_folder, "bin", "spim")
        self._sign_elf(pkg_bin)

        # Copy the exception handler (required at runtime)
        exc_src = os.path.join(self.source_folder, "CPU", "exceptions.s")
        copy(self, "exceptions.s", os.path.dirname(exc_src),
             os.path.join(self.package_folder, "share", "spim"))

    def _sign_elf(self, filepath):
        """Sign ELF binary for HarmonyOS execution."""
        if not os.path.exists(filepath):
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(sign_tool):
            return
        # Remove old signature
        subprocess.run([objcopy, "--remove-section", ".codesign", filepath],
                       capture_output=True, timeout=10)
        # Sign
        tmp = filepath + ".signed.tmp"
        subprocess.run([sign_tool, "sign", "-inFile", filepath,
                        "-outFile", tmp, "-selfSign", "1"],
                       capture_output=True, timeout=30)
        if os.path.exists(tmp):
            shutil.move(tmp, filepath)
            os.chmod(filepath, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/spim"]
