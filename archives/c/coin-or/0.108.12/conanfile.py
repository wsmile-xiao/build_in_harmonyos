#!/usr/bin/env python3
"""Conan recipe — coin-or 0.108.12 (COIN-OR Osi, Open Solver Interface, autotools).

Osi is a uniform C++ API for calling embedded LP/MIP solver libraries.
Dependencies: CoinUtils (COIN-OR utilities) + zlib.
License: Eclipse Public License 2.0 (EPL-2.0).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CoinorConan(ConanFile):
    name = "coin-or"
    version = "0.108.12"
    description = "COIN-OR Osi: Open Solver Interface — uniform C++ API for LP/MIP solvers"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Osi"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: dependencies must be published to the artifact repo first
        self.requires("coinutils/2.11.13")
        self.requires("zlib/1.3.1")

    def layout(self):
        # In-source build: COIN-OR recursive configure (top-level + Osi/ subdir)
        # does not tolerate out-of-source builds on HMDFS
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Explicit --build avoids config.guess temp-file failures on HMDFS
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        # Disable dependency tracking to avoid HMDFS temp file issues with config.status
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS workaround: set TMPDIR to a writable location under home
        _tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        # E165: Fix shebangs for HarmonyOS — use dynamic paths
        _config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        _ohos_shell = os.environ.get("OHOS_SHELL", "/system/bin/sh")
        for script in ["configure", "install-sh", "config.sub", "config.guess", "ltmain.sh"]:
            sp = os.path.join(self.source_folder, script)
            if os.path.exists(sp):
                self.run(f"sed -i '1s|#!/bin/bash|#!{_config_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#!/bin/sh|#!{_ohos_shell}|' '{sp}'")
                # Also handle "#! /bin/sh" (with space)
                self.run(f"sed -i '1s|#! /bin/sh|#!{_ohos_shell}|' '{sp}'")
        # E160: Fix config.guess (handle both "$UNAME_SYSTEM" and "${UNAME_SYSTEM}" patterns)
        for guess in [os.path.join(self.source_folder, p) for p in ["config.guess", "config/config.guess", "Osi/config.guess"]]:
            if os.path.exists(guess):
                self.run(r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
        # CoinUtils dependency paths for configure (--with-coinutils-*)
        _cu = self.dependencies["coinutils"]
        _cu_dir = _cu.package_folder
        _zl = self.dependencies["zlib"]
        _zl_dir = _zl.package_folder
        src = self.source_folder
        _shared = self.options.shared
        _static_flag = "--disable-shared" if not _shared else "--enable-shared"
        _shared_flag = "--enable-static" if not _shared else "--disable-static"
        # Build manually to avoid HMDFS issues with config.status temp files
        # (same approach as coinutils/2.11.13 recipe)
        self.run(f"cd '{src}' && "
                 f"TMPDIR={_tmpdir} "
                 f"./configure --prefix=/ "
                 f"--build=aarch64-unknown-linux-musl "
                 f"{_static_flag} {_shared_flag} --disable-dependency-tracking "
                 f"--with-coinutils-incdir={_cu_dir}/include/coin "
                 f"--with-coinutils-lib='-L{_cu_dir}/lib -L{_zl_dir}/lib -lCoinUtils -lz -lm'")
        # Patch all config.status files (root + Osi subdir) to fix HMDFS umask issue
        for cs in ["config.status", "Osi/config.status"]:
            csp = os.path.join(src, cs)
            if os.path.exists(csp):
                # Replace mktemp with mkdir to avoid HMDFS umask 077 issue
                self.run(f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' '{csp}'")
                # Replace fallback temp dir
                self.run(f"sed -i 's|tmp=\\./confstat\\$\\$$-\\$RANDOM|tmp=./conftmp|' '{csp}'")
                # Replace umask 077 with 022
                self.run(f"sed -i 's|umask 077|umask 022|g' '{csp}'")
                # Fix the tmp assignment so it actually sets $tmp (not just runs mkdir)
                self.run("sed -i 's|`mkdir -p \\./conftmp`|./conftmp|' '%s'" % csp)
                # Handle pre-patched form that echoes the dir
                self.run(f"sed -i 's|tmp=\\`(umask 022 \\&\\& mkdir -p ./conftmp) 2>/dev/null\\`|tmp=`(umask 022 \\&\\& mkdir -p ./conftmp \\&\\& echo ./conftmp) 2>/dev/null`|' '{csp}'")
                self.run(f"cd '{os.path.dirname(csp)}' && "
                         f"rm -rf conftmp confstat* && "
                         f"TMPDIR={_tmpdir} "
                         f"CONFIG_SHELL={_config_shell} "
                         f"{_config_shell} config.status")
        # Build only — no install in build() to avoid double install
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        # Run upstream test suite (Osi ships unit tests under Osi/src/OsiCommonTest)
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["Osi"]
        self.cpp_info.requires = ["coinutils::coinutils", "zlib::zlib"]
        # Osi headers include CoinUtils headers via quoted includes (e.g. "CoinPragma.hpp"),
        # which live under <coinutils>/include/coin. Expose that dir so consumers can
        # compile against Osi headers without manual -I flags.
        _cu_pkg = self.dependencies["coinutils"].package_folder
        self.cpp_info.includedirs = ["include", os.path.join(_cu_pkg, "include", "coin")]
