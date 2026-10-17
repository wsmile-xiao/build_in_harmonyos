#!/usr/bin/env python3
"""Conan recipe for grpcurl 1.9.3 — Go CLI tool for gRPC servers.

grpcurl is a pure Go project. The Go linker cannot mmap output files on
HarmonyOS (tmpfs MAP_SHARED restriction), so building from source is not
possible on this platform. Instead, this recipe downloads the official
pre-built static binary from GitHub releases, strips it, and signs it
with binary-sign-tool for HarmonyOS execution compatibility.

The source tarball is still downloaded in source() for reference and
reproducibility, per Conan conventions.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GrpcurlConan(ConanFile):
    name = "grpcurl"
    version = "1.9.3"
    description = "Like cURL, but for gRPC: command-line tool for interacting with gRPC servers"
    license = "MIT"
    homepage = "https://github.com/fullstorydev/grpcurl"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Download pre-built static binary from GitHub releases.
        # Go linker mmap fails on HarmonyOS tmpfs, so we use the official
        # release binary (CGO_ENABLED=0, static ELF, arm64).
        # Use mirror URLs for CI worker compatibility (R39: CI adds GitHub mirrors).
        binary_urls = [
            "https://github.com/fullstorydev/grpcurl/releases/download/v1.9.3/grpcurl_1.9.3_linux_arm64.tar.gz",
            "https://gh-proxy.com/https://github.com/fullstorydev/grpcurl/releases/download/v1.9.3/grpcurl_1.9.3_linux_arm64.tar.gz",
            "https://ghfast.top/https://github.com/fullstorydev/grpcurl/releases/download/v1.9.3/grpcurl_1.9.3_linux_arm64.tar.gz",
        ]
        binary_sha256 = "b20a00c1cb82ab81ec32696766d4076e99b4cb5ca0823a71767ba64dbea0f263"
        for url in binary_urls:
            try:
                get(self, url=url, sha256=binary_sha256)
                break
            except Exception:
                continue
        else:
            raise Exception("Failed to download grpcurl binary from all mirror URLs")

        grpcurl_bin = os.path.join(self.build_folder, "grpcurl")

        # Strip section headers to fix "bad shdr" issue (Go non-standard ELF layout).
        # This allows binary-sign-tool to add the .codesign section.
        strip_tool = shutil.which("strip") or shutil.which("llvm-strip")
        if strip_tool:
            subprocess.run([strip_tool, "--strip-all", grpcurl_bin], check=True)

        # Sign the binary for HarmonyOS execution (required by HMDFS).
        # binary-sign-tool is only available on HarmonyOS; on other platforms
        # the binary runs without signing.
        sign_tool = shutil.which("binary-sign-tool")
        if sign_tool:
            signed_bin = grpcurl_bin + "_signed"
            subprocess.run(
                [sign_tool, "sign", "-inFile", grpcurl_bin, "-outFile", signed_bin, "-selfSign", "1"],
                check=True
            )
            os.replace(signed_bin, grpcurl_bin)
            os.chmod(grpcurl_bin, 0o755)

    def package(self):
        copy(self, "grpcurl", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
