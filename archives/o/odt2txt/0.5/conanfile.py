#!/usr/bin/env python3
"""Conan recipe for odt2txt 0.5 — plain Makefile build (no configure script).

odt2txt converts OpenDocument files to raw text.
Build system: plain Makefile (GitHub archive has no configure script).
License: GPL-2.0-only

R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
"""
import os
import hashlib
import tarfile
import subprocess
import shutil

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class Odt2TxtConan(ConanFile):
    name = "odt2txt"
    version = "0.5"
    description = "Converts an OpenDocument or OpenOffice.org XML file to raw text"
    license = "GPL-2.0-only"
    homepage = "https://github.com/dstosberg/odt2txt"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R26: Terminal tools must be statically linked
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        """Download source using curl to bypass SSL certificate issues.
        Uses multiple URL fallbacks (codeload, ghfast mirror, direct GitHub).
        """
        sources = self.conan_data["sources"]
        expected_sha256 = sources["sha256"]
        filename = "odt2txt-0.5.tar.gz"

        # Multiple URL fallbacks for reliability
        urls = [
            "https://codeload.github.com/dstosberg/odt2txt/tar.gz/refs/tags/v0.5",
            "https://ghfast.top/https://github.com/dstosberg/odt2txt/archive/refs/tags/v0.5.tar.gz",
            "https://github.com/dstosberg/odt2txt/archive/refs/tags/v0.5.tar.gz",
        ]

        last_error = None
        for url in urls:
            try:
                self.output.info(f"Trying download from: {url}")
                subprocess.run(
                    ["curl", "-kL", "--connect-timeout", "30", "-o", filename, url],
                    check=True, cwd=self.source_folder
                )
                # Verify sha256
                with open(os.path.join(self.source_folder, filename), "rb") as f:
                    actual_sha256 = hashlib.sha256(f.read()).hexdigest()
                if actual_sha256 == expected_sha256:
                    self.output.info(f"Download successful from: {url}")
                    break
                else:
                    self.output.warning(f"sha256 mismatch from {url}: expected {expected_sha256}, got {actual_sha256}")
                    last_error = f"sha256 mismatch from {url}"
            except Exception as e:
                self.output.warning(f"Download failed from {url}: {e}")
                last_error = str(e)
        else:
            raise Exception(f"All download URLs failed. Last error: {last_error}")

        # Extract
        with tarfile.open(os.path.join(self.source_folder, filename), "r:gz") as tar:
            tar.extractall(path=self.source_folder)

        # Move contents from odt2txt-0.5/ to source root
        src_subdir = os.path.join(self.source_folder, "odt2txt-0.5")
        if os.path.isdir(src_subdir):
            for item in os.listdir(src_subdir):
                src_path = os.path.join(src_subdir, item)
                dst_path = os.path.join(self.source_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(src_subdir)

        # Fix permissions (tarfile may lose execute bits)
        for root, dirs, files in os.walk(self.source_folder):
            for fname in files:
                fpath = os.path.join(root, fname)
                if fname.endswith((".sh", ".py")):
                    os.chmod(fpath, 0o755)

    def generate(self):
        """Set up build environment with static linking (R26)."""
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        """Build using plain Makefile (no configure script).
        Autotools.make() sources the conanbuildenv script for CC, CFLAGS, LDFLAGS.
        """
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # No configure script — go straight to make
        autotools.make(target=None)

    def package(self):
        """Install using make install with DESTDIR staging."""
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        """Package info — odt2txt is a binary tool, not a library."""
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Define bindir for consumers
        self.cpp_info.bindirs = ["bin"]
