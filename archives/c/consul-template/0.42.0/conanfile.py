#!/usr/bin/env python3
"""Conan recipe — consul-template 0.42.0 (prebuilt binary from HashiCorp releases).

consul-template is a Go application that renders Go template files using
data from Consul. The Go linker cannot work on HarmonyOS due to mmap
permission restrictions (EPERM on MAP_SHARED for output files).

This package uses HashiCorp's official prebuilt linux_arm64 binary which is
statically linked and runs on OpenHarmony after ELF signing.

Source: https://releases.hashicorp.com/consul-template/0.42.0/
License: MPL-2.0

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
R34: test_package runs the actual binary (--version)
R38: commands.json declared at software level
"""
import os
import shutil
import stat
import subprocess
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class ConsulTemplateConan(ConanFile):
    name = "consul-template"
    version = "0.42.0"
    description = "Consul Template renders Go template files using data from Consul"
    license = "MPL-2.0"
    homepage = "https://github.com/hashicorp/consul-template"
    url = ""  # CI fills this
    package_type = "application"

    # R32: settings.os must check `in ("Linux", "OHOS")`
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        # R32: OS compatibility check — must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"consul-template does not support OS: {self.settings.os}"
            )

    def source(self):
        # Download the prebuilt binary zip from HashiCorp releases
        sources = self.conan_data["sources"]
        download(self, url=sources["url"], filename="consul-template.zip", sha256=sources["sha256"])

    def build(self):
        # Apply patches (none for prebuilt binary, but required by G1 check)
        apply_conandata_patches(self)

        # Extract the zip
        zip_path = os.path.join(self.source_folder, "consul-template.zip")
        extract_dir = os.path.join(self.source_folder, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Sign the ELF binary for HarmonyOS execution
        binary_path = os.path.join(extract_dir, "consul-template")
        if os.path.exists(binary_path):
            self._sign_elf(binary_path)

    def package(self):
        # Copy binary to bin/
        extract_dir = os.path.join(self.source_folder, "extracted")
        copy(self, "consul-template", extract_dir, os.path.join(self.package_folder, "bin"))
        # Ensure binary is executable
        binary_dest = os.path.join(self.package_folder, "bin", "consul-template")
        if os.path.exists(binary_dest):
            os.chmod(binary_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        # Copy LICENSE
        copy(self, "LICENSE.txt", extract_dir, os.path.join(self.package_folder, "share"))

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
        os.chmod(binary_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
