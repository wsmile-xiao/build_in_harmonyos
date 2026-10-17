#!/usr/bin/env python3
"""Conan recipe — coinor-dylp 1.10.4 (COIN-OR DyLP, dynamic simplex LP solver, autotools).

DyLP is a dynamic simplex LP solver written in C, with a C++ OsiDylp interface.
Dependencies: CoinUtils (COIN-OR utilities) + Osi (coin-or) + zlib.
License: Eclipse Public License 1.0 (EPL-1.0).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CoinordylpConan(ConanFile):
    name = "coinor-dylp"
    version = "1.10.4"
    description = "COIN-OR DyLP: dynamic simplex linear programming solver"
    license = "EPL-1.0"
    homepage = "https://github.com/coin-or/DyLP"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # config.guess/config.sub upgrade files (2024 versions with HarmonyOS support)
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: dependencies must be published to the artifact repo first
        self.requires("coinutils/2.11.13")
        self.requires("coin-or/0.108.12")
        self.requires("zlib/1.3.1")

    def layout(self):
        # In-source build: COIN-OR recursive configure (top-level + DyLP/ subdir)
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
        src = self.source_folder
        # E165: Fix shebangs for HarmonyOS — use dynamic paths
        _config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        _ohos_shell = os.environ.get("OHOS_SHELL", "/system/bin/sh")
        for script in ["configure", "install-sh", "config.sub", "config.guess", "ltmain.sh"]:
            sp = os.path.join(src, script)
            if os.path.exists(sp):
                self.run(f"sed -i '1s|#!/bin/bash|#!{_config_shell}|' '{sp}'")
                self.run(f"sed -i '1s|#!/bin/sh|#!{_ohos_shell}|' '{sp}'")
                # Also handle "#! /bin/sh" (with space)
                self.run(f"sed -i '1s|#! /bin/sh|#!{_ohos_shell}|' '{sp}'")
        # DyLP ships 2007-era config.guess/config.sub that cannot parse
        # aarch64-unknown-linux-musl or HarmonyOS. The minimal patches in
        # patches/ (applied by apply_conandata_patches above) add
        # aarch64/musl support to config.sub and a HarmonyOS branch to
        # config.guess for both the top-level and DyLP/ subdir copies.
        # Dependency paths for configure (--with-coinutils-*/--with-osi-*)
        _cu = self.dependencies["coinutils"]
        _cu_dir = _cu.package_folder
        _os = self.dependencies["coin-or"]
        _os_dir = _os.package_folder
        _zl = self.dependencies["zlib"]
        _zl_dir = _zl.package_folder
        _shared = self.options.shared
        _static_flag = "--disable-shared" if not _shared else "--enable-shared"
        _shared_flag = "--enable-static" if not _shared else "--disable-static"
        # Build manually to avoid HMDFS issues with config.status temp files
        # (same approach as coinutils/2.11.13 and coin-or/0.108.12 recipes)
        self.run(f"cd '{src}' && "
                 f"TMPDIR={_tmpdir} "
                 f"./configure --prefix=/ "
                 f"--build=aarch64-unknown-linux-musl "
                 f"{_static_flag} {_shared_flag} --disable-dependency-tracking "
                 f"--with-coinutils-incdir={_cu_dir}/include/coin "
                 f"--with-coinutils-lib='-L{_cu_dir}/lib -L{_zl_dir}/lib -lCoinUtils -lz -lm' "
                 f"--with-osi-incdir={_os_dir}/include/coin "
                 f"--with-osi-lib='-L{_os_dir}/lib -L{_cu_dir}/lib -L{_zl_dir}/lib -lOsi -lCoinUtils -lz -lm'")
        # Patch all config.status files (root + DyLP subdir) to fix HMDFS umask issue
        for cs in ["config.status", "DyLP/config.status"]:
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
        # Fix broken dependency paths in the coin-or/coinutils libtool archives.
        # conan's relocatable packaging rewrote absolute paths like
        # <prefix>/lib/libCoinUtils.la into //lib/libCoinUtils.la, which makes
        # libtool fail when linking libOsiDylp. Restore the real absolute paths.
        for la_file, old_path, new_path in [
            (os.path.join(_os_dir, "lib", "libOsi.la"), "//lib/libCoinUtils.la",
             os.path.join(_cu_dir, "lib", "libCoinUtils.la")),
            (os.path.join(_os_dir, "lib", "libOsiCommonTests.la"), "//lib/libOsi.la",
             os.path.join(_os_dir, "lib", "libOsi.la")),
            (os.path.join(_os_dir, "lib", "libOsiCommonTests.la"), "//lib/libCoinUtils.la",
             os.path.join(_cu_dir, "lib", "libCoinUtils.la")),
        ]:
            if os.path.exists(la_file):
                with open(la_file, "r", encoding="utf-8") as _f:
                    _content = _f.read()
                if old_path in _content:
                    self.output.info(f"patching {os.path.basename(la_file)}: {old_path} -> {new_path}")
                    with open(la_file, "w", encoding="utf-8") as _f:
                        _f.write(_content.replace(old_path, new_path))
        # Build only — no install in build() to avoid double install
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        # Run upstream test suite (dylp test/ dir; skipped when OsiTests absent)
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["OsiDylp", "Dylp"]
        self.cpp_info.requires = ["coin-or::coin-or", "coinutils::coinutils", "zlib::zlib"]
        # DyLP headers include CoinUtils/Osi headers via quoted includes
        # (e.g. "CoinPackedMatrix.hpp"), which live under <coinutils>/include/coin
        # and <coin-or>/include/coin. Expose those dirs so consumers can compile
        # against DyLP headers without manual -I flags.
        _cu_pkg = self.dependencies["coinutils"].package_folder
        _os_pkg = self.dependencies["coin-or"].package_folder
        # DyLP headers live under include/coin (dylp.h internally uses
        # #include <dylib_io.h>), so expose include/coin itself, plus the
        # CoinUtils/Osi include/coin dirs for quoted includes like "CoinPragma.hpp".
        self.cpp_info.includedirs = ["include/coin", "include",
                                     os.path.join(_cu_pkg, "include", "coin"),
                                     os.path.join(_os_pkg, "include", "coin")]
