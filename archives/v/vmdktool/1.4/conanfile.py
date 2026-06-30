#!/usr/bin/env python3
"""Conan recipe for vmdktool 1.4 — BSD-style Makefile (no configure script).

vmdktool converts raw filesystems to VMDK files and vice versa.
Build system: simple BSD Makefile (CC, CFLAGS, PREFIX, DESTDIR).
License: BSD-2-Clause.

R26: Terminal tool — statically linked.
"""
import os
import subprocess
import hashlib
import tarfile
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class VmdktoolConan(ConanFile):
    name = "vmdktool"
    version = "1.4"
    description = "Converts raw filesystems to VMDK files and vice versa"
    license = "BSD-2-Clause"
    homepage = "https://people.freebsd.org/~brian/vmdktool/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external Conan dependencies; zlib is a system library
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use curl -kL to download due to SSL certificate issues on this platform
        url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"]["sha256"]

        tmpfile = os.path.join(self.source_folder, "vmdktool-1.4.tar.gz")
        subprocess.run(["curl", "-kL", "-o", tmpfile, url], check=True)

        # Verify sha256
        actual_sha256 = hashlib.sha256(open(tmpfile, "rb").read()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Exception(f"sha256 mismatch: expected {expected_sha256}, got {actual_sha256}")

        # Extract with strip_root (move contents of vmdktool-1.4/ to source_folder)
        import tempfile
        tmp_extract = tempfile.mkdtemp(dir=self.source_folder)
        with tarfile.open(tmpfile, "r:gz") as tf:
            tf.extractall(tmp_extract)

        # Move contents of the wrapper directory to source_folder
        wrapper = os.path.join(tmp_extract, "vmdktool-1.4")
        if os.path.isdir(wrapper):
            for item in os.listdir(wrapper):
                src = os.path.join(wrapper, item)
                dst = os.path.join(self.source_folder, item)
                shutil.move(src, dst)
            os.rmdir(wrapper)
        else:
            # If no wrapper, move all contents
            for item in os.listdir(tmp_extract):
                src = os.path.join(tmp_extract, item)
                dst = os.path.join(self.source_folder, item)
                shutil.move(src, dst)
        os.rmdir(tmp_extract)

        # Remove tarball
        os.unlink(tmpfile)

    def generate(self):
        # R26: Terminal tools must be statically linked
        pass  # Handled in build() via LDLIBS

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        cc = "clang"
        cflags = "-fPIC -O2 -pipe -g"
        ldlibs = "-static -L/storage/Users/currentUser/usr/local/lib -lz"

        self.run(
            f'make -j1 CC={cc} CFLAGS="{cflags}" '
            f'LDLIBS="{ldlibs}" '
            f'-C "{src_dir}"'
        )

    def package(self):
        src_dir = self.source_folder

        # Install binary
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(src_dir, "vmdktool"),
            os.path.join(bin_dir, "vmdktool"),
        )

        # Install man page
        man_dir = os.path.join(self.package_folder, "share", "man", "man8")
        os.makedirs(man_dir, exist_ok=True)
        man_src = os.path.join(src_dir, "vmdktool.8")
        if os.path.exists(man_src):
            shutil.copy2(man_src, os.path.join(man_dir, "vmdktool.8"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
