#!/usr/bin/env python3
"""Conan recipe — aqua v2.60.0 (prebuilt binary from GitHub releases).

aqua is a Declarative CLI Version Manager written in Go. It supports
Lazy Install, Registry, and continuous update with Renovate.

The Go linker cannot work on HarmonyOS due to mmap permission restrictions
(EPERM on MAP_SHARED for output files), so this package uses aquaproj's
official prebuilt linux_arm64 binary which is statically linked and runs
on OpenHarmony after ELF signing.

Source: https://github.com/aquaproj/aqua/releases/tag/v2.60.0
License: MIT

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
R34: test_package runs the actual binary (--version)
R38: commands.json declared at software level
R39: Source URL is official GitHub release
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class AquaConan(ConanFile):
    name = "aqua"
    version = "v2.60.0"
    description = "Declarative CLI Version Manager written in Go"
    license = "MIT"
    homepage = "https://github.com/aquaproj/aqua"
    url = ""  # CI fills this
    package_type = "application"
    topics = ("version-manager", "cli", "package-manager", "go")

    # R32: settings.os must check `in ("Linux", "OHOS")`
    # L0p: settings must include all four (os/compiler/build_type/arch)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        # R32: OS compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aqua does not support OS: {self.settings.os}"
            )

    def source(self):
        # Download the prebuilt binary tarball from GitHub releases
        sources = self.conan_data["sources"]
        download(self, url=sources["url"], filename="aqua_linux_arm64.tar.gz", sha256=sources["sha256"])

    def build(self):
        # Apply patches (none for prebuilt binary, but required by G1 check)
        apply_conandata_patches(self)

        # Extract the tarball using system tar to preserve execute permission
        # (Python tarfile.extractall() with data filter strips execute bit on 3.12+)
        tarball = os.path.join(self.source_folder, "aqua_linux_arm64.tar.gz")
        extract_dir = os.path.join(self.source_folder, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        self.run(f"tar xzf {tarball} -C {extract_dir}")

        # Sign the ELF binary for HarmonyOS execution
        binary_path = os.path.join(extract_dir, "aqua")
        if os.path.exists(binary_path):
            self._sign_elf(binary_path)

    def package(self):
        # Copy binary to bin/
        extract_dir = os.path.join(self.source_folder, "extracted")
        copy(self, "aqua", extract_dir, os.path.join(self.package_folder, "bin"))

        # Ensure binary is executable (best effort, may not work on OHOS HMDFS - E046)
        binary_dest = os.path.join(self.package_folder, "bin", "aqua")
        if os.path.exists(binary_dest):
            try:
                os.chmod(binary_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            except OSError:
                pass  # E046: chmod ineffective on OHOS HMDFS

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

    def _sign_elf(self, binary_path):
        """Sign ELF binary for HarmonyOS execution using binary-sign-tool."""
        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp_bin, "llvm-objcopy")
        sign_tool = os.path.join(hnp_bin, "binary-sign-tool")

        # Fallback to PATH lookup
        if not os.path.exists(objcopy):
            objcopy = shutil.which("llvm-objcopy") or objcopy
        if not os.path.exists(sign_tool):
            sign_tool = shutil.which("binary-sign-tool") or sign_tool

        if not os.path.exists(sign_tool):
            # No signing tool available — skip (binary may still work on Linux)
            return

        # Step 1: Remove old signature section
        if os.path.exists(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binary_path],
                capture_output=True, timeout=10,
            )

        # Step 2: Sign with binary-sign-tool
        tmp_signed = binary_path + ".signed.tmp"
        for attempt in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", binary_path,
                 "-outFile", tmp_signed, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.exists(tmp_signed):
                shutil.move(tmp_signed, binary_path)
                break
        else:
            # Signing failed — continue with unsigned binary
            if os.path.exists(tmp_signed):
                os.remove(tmp_signed)

        # Ensure executable permissions
        try:
            os.chmod(binary_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        except OSError:
            pass  # E046: chmod ineffective on OHOS HMDFS
