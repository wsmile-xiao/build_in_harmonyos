#!/usr/bin/env python3
"""Conan recipe for nuttcp 8.2.2.

nuttcp - TCP/UDP network throughput measurement tool.
Build system: plain Makefile (no configure, no autotools).
Single C source file, no external dependencies.
"""
import os
import ssl
import hashlib
import tarfile
import tempfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class NuttcpConan(ConanFile):
    name = "nuttcp"
    version = "8.2.2"
    description = "nuttcp - TCP/UDP network throughput measurement tool"
    license = "MIT"
    homepage = "https://www.nuttcp.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        # nuttcp.net SSL certificate is expired; download with SSL disabled
        src_info = self.conan_data["sources"]
        url = src_info["url"]
        expected_sha = src_info.get("sha256", "")
        dest = self.source_folder

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with tempfile.NamedTemporaryFile(suffix=".tar.bz2", delete=False) as tmp:
            with urllib.request.urlopen(url, context=ctx) as resp:
                tmp.write(resp.read())
            tmp_path = tmp.name

        # Verify checksum
        if expected_sha:
            actual_sha = hashlib.sha256(open(tmp_path, "rb").read()).hexdigest()
            if actual_sha != expected_sha:
                raise Exception(f"SHA256 mismatch: expected {expected_sha}, got {actual_sha}")

        # Extract with strip_root
        with tarfile.open(tmp_path, "r:bz2") as tf:
            members = tf.getmembers()
            if members:
                root = members[0].name.split("/")[0]
                # Check if all members share the same root directory
                all_under_root = all(m.name == root or m.name.startswith(root + "/") for m in members)
                for m in members:
                    if all_under_root:
                        parts = m.name.split("/", 1)
                        if len(parts) > 1:
                            m.name = parts[1]
                        else:
                            continue  # skip root dir entry itself
                    if m.name:
                        tf.extract(m, dest)

        os.unlink(tmp_path)

    def build(self):
        apply_conandata_patches(self)
        cc = str(self.settings.compiler) or "clang"
        # nuttcp Makefile uses CC and OPT; pass through Conan's compiler
        self.run(f"make CC=\"{cc}\" OPT=\"-fPIC -O2\" -j1", cwd=self.source_folder)

    def package(self):
        # Copy the binary and man page
        copy(self, "nuttcp-8.2.2", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Rename to 'nuttcp' (without version suffix)
        old_path = os.path.join(self.package_folder, "bin", "nuttcp-8.2.2")
        new_path = os.path.join(self.package_folder, "bin", "nuttcp")
        os.rename(old_path, new_path)
        # Copy man page
        copy(self, "nuttcp.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
