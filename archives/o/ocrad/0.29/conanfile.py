#!/usr/bin/env python3
"""Conan recipe for ocrad 0.29 — GNU Optical Character Recognition program.

ocrad is a custom-configure (non-standard autotools) C++ project that produces
both a CLI binary (ocrad) and a static library (libocrad.a). The configure
script accepts CXX, CXXFLAGS, CPPFLAGS, LDFLAGS, LIBS as makefile variables.

The source tarball is distributed in .tar.lz (lzip) format, which Conan's
built-in get() does not support. The source() method handles decompression
by parsing the lzip container and feeding the LZMA stream to Python's lzma.

Dependencies:
  - libpng/1.6.58.2 (PNG image I/O, shared library, published on ohpcd)
  - zlib           (pulled transitively via libpng, static library)
"""
import os
import struct
import lzma
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    download, copy,
    apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OcradConan(ConanFile):
    name = "ocrad"
    version = "0.29"
    description = "GNU Ocrad - Optical Character Recognition program and library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/ocrad/"
    url = ""  # CI fills this

    # Produces both a CLI binary and a static library
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib comes transitively via libpng
        self.requires("libpng/1.6.58.2")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ocrad is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # Conan's get() does not support .tar.lz (lzip) format.
        # Download manually, decompress lzip→LZMA, then extract the .tar.
        src = self.conan_data["sources"]
        url = src["url"]

        lz_filename = "ocrad-0.29.tar.lz"
        download(self, url, lz_filename, verify=True)

        tar_filename = "ocrad-0.29.tar"
        self._decompress_lzip(lz_filename, tar_filename)
        os.remove(lz_filename)

        # Extract .tar using Python tarfile
        with tarfile.open(tar_filename) as tf:
            tf.extractall(".")
        os.remove(tar_filename)

        # strip_root: promote contents from ocrad-0.29/ to current directory
        subdir = "ocrad-0.29"
        if os.path.isdir(subdir):
            for item in os.listdir(subdir):
                src_path = os.path.join(subdir, item)
                dst_path = os.path.join(".", item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(subdir)

    @staticmethod
    def _decompress_lzip(input_file, output_file):
        """Decompress a .tar.lz (lzip) file to a .tar file.

        The lzip format is: 6-byte header + LZMA stream + 20-byte trailer.
        We reconstruct an LZMA-ALONE header and use Python's lzma module.
        """
        with open(input_file, "rb") as f:
            data = f.read()

        # Validate magic
        if data[:4] != b"LZIP":
            raise ValueError(f"Not a lzip file: {input_file}")

        # Trailer (last 20 bytes): CRC32(4) + data_size(8) + member_size(8)
        crc32_val, data_size, member_size = struct.unpack("<IQQ", data[-20:])

        # LZMA stream is between header(6) and trailer(20)
        lzma_stream = data[6:-20]

        # Reconstruct LZMA ALONE format header:
        #   1 byte properties (lc=3,lp=0,pb=2 → 0x5d)
        #   4 bytes dict_size (little-endian)
        #   8 bytes uncompressed size (little-endian, -1 for unknown)
        props = 0x5D
        dict_size = 8388608  # 8 MiB
        lzma_header = (
            bytes([props])
            + struct.pack("<I", dict_size)
            + struct.pack("<q", data_size)
        )

        result = lzma.decompress(lzma_header + lzma_stream, format=lzma.FORMAT_ALONE)

        with open(output_file, "wb") as f:
            f.write(result)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from libpng/zlib into the build environment
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # ocrad's custom configure doesn't support --enable-static/--disable-shared
        tc.configure_args = []
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs
        # (libpng16.so is shared-only). The configure/make conftest and the
        # resulting binary need LD_LIBRARY_PATH pointing at dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        # Ensure configure is executable (extraction may not preserve permissions)
        configure_path = os.path.join(self.source_folder, "configure")
        os.chmod(configure_path, 0o755)
        # ocrad's custom configure sets CXX=g++ by default, overriding the env.
        # Pass CXX/CXXFLAGS as configure args so the generated Makefile uses
        # the Conan toolchain compiler. CPPFLAGS/LDFLAGS/LIBS are passed to
        # make (not configure) since configure doesn't need them.
        self.run(
            f'./configure --prefix="{self.package_folder}" '
            f'CXX="$CXX" CXXFLAGS="$CXXFLAGS"',
            env="conanbuild", cwd=self.source_folder,
        )
        # Pass dependency flags as make command-line variables, which override
        # the Makefile values. The conanbuild env (from AutotoolsDeps) sets
        # CPPFLAGS/LDFLAGS/LIBS with correct resolved paths for all deps
        # including transitive (zlib). Shell expands $VAR before make sees them.
        self.run(
            'make -j1 CPPFLAGS="$CPPFLAGS" LDFLAGS="$LDFLAGS" LIBS="$LIBS"',
            env="conanbuild", cwd=self.source_folder,
        )

    def package(self):
        # Manual install: ocrad's Makefile uses the 'install' command which may
        # not be available on all platforms. Use conan.tools.files.copy instead.
        import stat
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "ocrad", src, bin_dir)
        copy(self, "libocrad.a", src, os.path.join(self.package_folder, "lib"))
        copy(self, "ocradlib.h", src, os.path.join(self.package_folder, "include"))
        # Ensure binary is executable (HMDFS may not preserve permissions, E046)
        bin_path = os.path.join(bin_dir, "ocrad")
        if os.path.exists(bin_path):
            os.chmod(bin_path, os.stat(bin_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.libs = ["ocrad"]
        self.cpp_info.bindirs = ["bin"]
