#!/usr/bin/env python3
"""Conan recipe — CoinUtils 2.11.13 (COIN-OR utilities, autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CoinutilsConan(ConanFile):
    name = "coinutils"
    version = "2.11.13"
    description = "COIN-OR utilities"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/CoinUtils"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # CoinUtils doesn't support out-of-source builds on HMDFS
        # Use in-source build to avoid config.status temp file issues
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
                # Also handle "#! /bin/sh" (with space) which some configure scripts use
                self.run(f"sed -i '1s|#! /bin/sh|#!{_ohos_shell}|' '{sp}'")
        # E160: Fix config.guess (handle both "$UNAME_SYSTEM" and "${UNAME_SYSTEM}" patterns)
        for guess in [os.path.join(self.source_folder, p) for p in ["config.guess", "config/config.guess", "utils/config.guess", "CoinUtils/config.guess"]]:
            if os.path.exists(guess):
                self.run(r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{guess}'")
        # Build manually to avoid HMDFS issues with config.status temp files
        # HMDFS blocks mktemp -d with umask 077 (./confstat*/). Workaround:
        # 1. Run configure (succeeds, generates config.status, Makefile stays empty)
        # 2. Patch config.status to use umask 022 + fixed temp dir
        # 3. Re-run config.status to create proper Makefiles
        # 4. make (no install — package() handles install via DESTDIR)
        # 5. make check (upstream tests)
        src = self.source_folder
        _shared = self.options.shared
        _static_flag = "--disable-shared" if not _shared else "--enable-shared"
        _shared_flag = "--enable-static" if not _shared else "--disable-static"
        self.run(f"cd '{src}' && "
                 f"TMPDIR={_tmpdir} "
                 f"./configure --prefix=/ "
                 f"--build=aarch64-unknown-linux-musl "
                 f"{_static_flag} {_shared_flag} --disable-dependency-tracking")
        # Patch all config.status files (root + CoinUtils subdir) to fix HMDFS umask issue
        for cs in ["config.status", "CoinUtils/config.status"]:
            csp = os.path.join(src, cs)
            if os.path.exists(csp):
                # Replace mktemp with mkdir to avoid HMDFS umask 077 issue
                self.run(f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' '{csp}'")
                # Replace fallback temp dir
                self.run(f"sed -i 's|tmp=\\./confstat\\$\\$$-\\$RANDOM|tmp=./conftmp|' '{csp}'")
                # Replace umask 077 with 022
                self.run(f"sed -i 's|umask 077|umask 022|g' '{csp}'")
                # Fix the tmp assignment so it actually sets $tmp (not just runs mkdir)
                self.run(f"sed -i 's|\`mkdir -p \\./conftmp\`|./conftmp|' '{csp}'")
                self.run(f"cd '{os.path.dirname(csp)}' && "
                         f"rm -rf conftmp confstat* && "
                         f"TMPDIR={_tmpdir} "
                         f"CONFIG_SHELL={_config_shell} "
                         f"{_config_shell} config.status")
        # Fix broken .lo files (HMDFS truncates libtool .lo writes)
        self.run(f"cd '{src}/CoinUtils/src' && for f in *.lo; do "
                 f"grep -q pic_object \"$f\" || {{ "
                 f"n=${{f%.lo}}; "
                 f"printf '# %s - libtool object\\npic_object=.libs/%s.o\\nnon_pic_object=%s.o\\n' \"$f\" \"$n\" \"$n\" > \"$f\"; "
                 f"}}; done")
        # Build only — no install in build() to avoid double install
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        # Run upstream test suite
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["CoinUtils"]