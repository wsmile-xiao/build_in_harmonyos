#!/usr/bin/env python3
"""Conan recipe — moe 1.16 (Autotools).

Console text editor for ISO-8859 and ASCII character encodings.
R26: Terminal tools must be statically linked.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MoeConan(ConanFile):
    name = "moe"
    version = "1.16"
    description = "Console text editor for ISO-8859 and ASCII character encodings"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/moe/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # moe source is distributed as .tar.lz; Conan's get() doesn't
        # support lzip, so we download and decompress manually.
        import urllib.request
        import ssl
        import tarfile
        import io
        import hashlib
        import pathlib

        src_info = self.conan_data["sources"]
        url = src_info["url"]
        expected_sha = src_info.get("sha256", "")

        # Download
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "conan/moe"})
        data = urllib.request.urlopen(req, timeout=300, context=ctx).read()

        # Verify SHA256
        if expected_sha:
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected_sha:
                raise Exception(f"SHA256 mismatch: expected {expected_sha}, got {actual}")

        # Decompress .tar.lz using system lzip
        tmp_lz = os.path.join(self.source_folder, "_moe.tar.lz")
        tmp_tar = os.path.join(self.source_folder, "_moe.tar")
        with open(tmp_lz, "wb") as f:
            f.write(data)
        subprocess.run(["lzip", "-d", "-k", "-f", tmp_lz], check=True)

        # Extract tar
        with tarfile.open(tmp_tar, mode="r:") as tf:
            tf.extractall(self.source_folder)
        os.unlink(tmp_lz)
        os.unlink(tmp_tar)

        # Promote single subdirectory
        src = pathlib.Path(self.source_folder)
        children = [c for c in src.iterdir() if not c.name.startswith("_") and not c.name.startswith(".")]
        if len(children) == 1 and children[0].is_dir():
            sub = children[0]
            for item in list(sub.iterdir()):
                shutil.move(str(item), src / item.name)
            sub.rmdir()

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        # moe's configure accepts CXX, CXXFLAGS, LDFLAGS as command-line args
        # E053: Must use clang++ instead of g++/c++ on HarmonyOS
        ncurses_inc = "/storage/Users/currentUser/usr/local/include"
        ncurses_lib = "/storage/Users/currentUser/usr/local/lib"
        tc.configure_args.append(f"CXX=clang++")
        tc.configure_args.append(f"CXXFLAGS=-O2 -fPIC -I{ncurses_inc}")
        tc.configure_args.append(f"LDFLAGS=-static -L{ncurses_lib}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["moe"]
