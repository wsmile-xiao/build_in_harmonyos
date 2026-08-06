#!/usr/bin/env python3
"""Conan recipe for LibRHash 1.4.4.

LibRHash is the C library shipped by the RHash project.  This recipe builds the
static library only, avoiding shared-library symlinks on OHOS/HMDFS and keeping
optional OpenSSL/gettext dependencies disabled for a dependency-free W0 path.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import chdir, copy, get, mkdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibRHashConan(ConanFile):
    name = "librhash"
    version = "1.4.4"
    description = "Portable C library for computing many hash functions"
    license = "0BSD"
    homepage = "https://github.com/rhash/RHash"
    url = ""

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executable(self, key, default):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers:
            return compilers.get(key, default)
        return default

    def _ar_executable(self, cc):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers and compilers.get("ar"):
            return compilers["ar"]
        try:
            ar = subprocess.check_output([cc, "--print-prog-name=llvm-ar"], text=True).strip()
            if ar:
                return ar
        except (OSError, subprocess.SubprocessError):
            pass
        return "llvm-ar"

    def _rhash_xversion(self):
        major, minor, patch = (int(part) for part in self.version.split("."))
        return f"0x{major:02x}{minor:02x}{patch:02x}00"

    def _build_static_without_make(self, cc, ar):
        sources = [
            "algorithms.c", "byte_order.c", "plug_openssl.c", "rhash.c",
            "rhash_torrent.c", "aich.c", "blake2b.c", "blake2s.c", "crc32.c",
            "ed2k.c", "edonr.c", "hex.c", "md4.c", "md5.c", "sha1.c",
            "sha256.c", "sha512.c", "sha3.c", "ripemd-160.c", "gost12.c",
            "gost94.c", "has160.c", "snefru.c", "tiger.c", "tiger_sbox.c",
            "tth.c", "torrent.c", "util.c", "whirlpool.c", "whirlpool_sbox.c",
        ]
        cflags = f"-O2 -DNDEBUG -DRHASH_XVERSION={self._rhash_xversion()}"
        objects = []
        with chdir(self, os.path.join(self.source_folder, "librhash")):
            for source in sources:
                obj = source[:-2] + ".o"
                self.run(f"{cc} -c {cflags} {source} -o {obj}")
                objects.append(obj)
            self.run(f"{ar} -cqs librhash.a {' '.join(objects)}")
            self.run(f"{cc} -c {cflags} test_lib.c -o test_lib.o")
            self.run(f"{cc} -c {cflags} test_utils.c -o test_utils.o")
            self.run(f"{cc} {cflags} test_lib.o test_utils.o librhash.a -static -o test_static")
            self.run("./test_static")

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_executable("c", "clang")
        ar = self._ar_executable(cc)
        default_shell = "/data/service/hnp/bin/bash" if self.settings.os == "OHOS" else "sh"
        config_shell = os.environ.get("CONFIG_SHELL", default_shell)
        build_tmp = os.path.join(self.build_folder, "tmp")
        mkdir(self, build_tmp)

        configure_args = [
            "--prefix=/",
            f"--cc={cc}",
            f"--ar={ar}",
            "--enable-static",
            "--enable-lib-static",
            "--disable-lib-shared",
            "--disable-gettext",
            "--disable-openssl",
            "--disable-symlinks",
        ]

        with chdir(self, self.source_folder):
            self.run(
                "TMPDIR={tmp} CONFIG_SHELL={shell} {shell} ./configure {args}".format(
                    tmp=build_tmp,
                    shell=config_shell,
                    args=" ".join(configure_args),
                )
            )
            make = shutil.which("make") or shutil.which("gmake")
            if make:
                self.run(f"{make} -j1 lib-static")
                self.run(f"{make} -j1 test-lib-static")
            else:
                self.output.warning("make not found; building LibRHash static library with recipe fallback")
                self._build_static_without_make(cc, ar)

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "librhash.a", os.path.join(self.source_folder, "librhash"), os.path.join(self.package_folder, "lib"))
        copy(self, "rhash.h", os.path.join(self.source_folder, "librhash"), os.path.join(self.package_folder, "include"))
        copy(self, "rhash_torrent.h", os.path.join(self.source_folder, "librhash"), os.path.join(self.package_folder, "include"))
        copy(self, "librhash.pc", os.path.join(self.source_folder, "dist"), os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["rhash"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "librhash")
        self.cpp_info.set_property("cmake_target_name", "librhash::librhash")
