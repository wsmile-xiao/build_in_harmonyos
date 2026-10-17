#!/usr/bin/env python3
"""Conan recipe for zutils — Utilities dealing with compressed files.

zutils provides zcat, zcmp, zdiff, zgrep, ztest, zupdate commands that
transparently handle gzip, bzip2, lzip, and xz compressed files.

Source is distributed as .tar.lz (lzip compressed tar). Conan's built-in
extraction does not support lzip, so a custom source() method decompresses
the lzip format using Python's lzma module.
"""
import lzma
import os
import tarfile

from conan import ConanFile
from conan.tools.files import download, check_sha256, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZutilsConan(ConanFile):
    name = "zutils"
    version = "1.15"
    description = "Utilities transparently handling gzip, bzip2, lzip, and xz compressed files"
    license = "GPL-2.0-or-later"
    homepage = "https://savannah.gnu.org/projects/zutils/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Custom source extraction for .tar.lz (lzip) format.
        # Conan's built-in get() does not support lzip compression.
        sources = self.conan_data["sources"]
        url = sources["url"]
        filename = os.path.basename(url)

        # Download the .tar.lz file
        download(self, url, filename)
        check_sha256(self, filename, sources["sha256"])

        # Decompress lzip format using Python's lzma module.
        # Lzip format: 6-byte header (LZIP magic + version + coded_dict_size)
        # followed by a raw LZMA1 stream and a 20-byte trailer.
        lzip_path = os.path.join(self.source_folder, filename)
        with open(lzip_path, "rb") as f:
            data = f.read()

        if data[:4] != b"LZIP":
            raise Exception("Not a lzip file: missing LZIP magic")

        dict_byte = data[5]
        base = 1 << (dict_byte & 0x1F)
        if dict_byte > 0x1F:
            frac = (dict_byte >> 5) & 0x07
            dict_size = base + (base // 16) * frac
        else:
            dict_size = base

        # Decompress the LZMA1 stream (skip 6-byte lzip header)
        lzma_data = data[6:]
        filters = [{"id": lzma.FILTER_LZMA1, "dict_size": dict_size,
                     "lc": 3, "lp": 0, "pb": 2}]
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        tar_data = dec.decompress(lzma_data)

        # Write the decompressed .tar and extract with strip_root
        tar_path = lzip_path.replace(".tar.lz", ".tar")
        with open(tar_path, "wb") as f:
            f.write(tar_data)

        with tarfile.open(tar_path) as tf:
            members = tf.getmembers()
            if members:
                root = members[0].name.split("/")[0]
                for m in members:
                    if m.name.startswith(root + "/"):
                        m.name = m.name[len(root) + 1:]
                        if m.name:
                            tf.extract(m)
                    elif m.name == root:
                        continue

        # Clean up intermediate files
        os.unlink(lzip_path)
        os.unlink(tar_path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # zutils configure script sets CXX=g++ unconditionally (line 23),
        # which overrides any environment variable. Pass CXX as a configure
        # argument to override it with the profile's compiler.
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cpp = compilers.get("cpp", "clang++")
        tc.configure_args.append(f"CXX={cpp}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
