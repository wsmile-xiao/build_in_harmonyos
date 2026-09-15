#!/usr/bin/env python3
"""Conan recipe for clzip 1.16 — LZMA compressor for the lzip format.

clzip is a command-line compression tool (not a library), written in C.
It uses a custom configure script (not GNU autoconf), sharing the same
build framework as the rest of the lzip family (same author, Antonio Diaz
Diaz), and is pure C (CC).

E095: the lzip-family custom configure script does not read the $CC
environment variable; it requires CC=<compiler> as a command-line argument.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    copy,
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ClzipConan(ConanFile):
    name = "clzip"
    version = "1.16"
    description = "LZMA lossless data compressor for the lzip format"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/lzip/clzip.html"
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
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: get the compiler from Conan conf, not shell env. Prefer the
        # configured OHOS clang; fall back to PATH lookup only if that path
        # does not actually exist on the worker.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if cc and os.path.exists(cc):
            return cc
        return shutil.which("clang") or "clang"

    def _sdk_llvm_libdir(self):
        # OHOS clang spawns lld for linking; lld's RUNPATH ($ORIGIN/../lib)
        # points into the SDK llvm/lib, which ships the matching libxml2.so.16.
        # On CI workers the ambient LD_LIBRARY_PATH can shadow that dir with an
        # ABI-incompatible libxml2.so.16, making lld fail. Prepend the SDK
        # llvm/lib so the correct library is found first. Only active on OHOS.
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._cc()
        cc_which = shutil.which(cc) or cc
        cc_real = os.path.realpath(cc_which)
        llvm_lib = os.path.join(
            os.path.dirname(os.path.dirname(cc_real)), "lib"
        )
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _build_environment(self):
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path for lld: {sdk_llvm_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return env

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E095: the lzip-family custom configure script (not autoconf) does
        # not read the $CC env var; it requires CC=<compiler> as a command-
        # line argument. R33: get the compiler from Conan conf, not shell env.
        cc = self._cc()
        tc.configure_args.append(f"CC={cc}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Wrap configure + make + make check in the SDK runtime path so lld
        # finds the matching libxml2 (see _sdk_llvm_libdir). package() only
        # calls Conan copy() (no clang/lld), so it needs no such wrap.
        with self._build_environment().vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j1"])
            # Run the official upstream test suite. clzip ships a comprehensive
            # POSIX shell test suite (testsuite/check.sh, invoked by
            # `make check`) covering compression/decompression roundtrip, bad
            # input, truncation, multi-member files, header variants and option
            # handling. Executed here so CI L1c can verify real upstream test
            # execution from the conan create log.
            autotools.make(args=["check"])

    def package(self):
        # OHOS lacks the coreutils `install` command, so the upstream
        # `make install` (install-bin/install-man targets) fails with
        # "install: inaccessible or not found". Manually copy the built
        # binary and the shipped man page instead, mirroring the upstream
        # Makefile install rules (755 for the binary, 644 for the man page).
        # The man page doc/clzip.1 ships prebuilt in the source tarball.
        dest_bin = os.path.join(self.package_folder, "bin")
        copy(self, "clzip", src=self.build_folder, dst=dest_bin)
        clzip_bin = os.path.join(dest_bin, "clzip")
        if os.path.exists(clzip_bin):
            os.chmod(clzip_bin, 0o755)
        copy(self, "clzip.1",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
