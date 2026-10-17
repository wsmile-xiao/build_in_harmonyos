#!/usr/bin/env python3
"""Conan recipe — afnix 3.8.0 (Afnix writing system).

Afnix uses a custom build system (afnix-setup + make), not autotools.
Reference: http://www.afnix.org
"""
import os

from conan import ConanFile
from conan.tools.files import get, patch, chdir


class AfnixConan(ConanFile):
    name = "afnix"
    version = "3.8.0"
    description = "Afnix writing system — multi-threaded functional programming language"
    license = "Afnix free software license (BSD-like)"
    homepage = "http://www.afnix.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # Patches declared here (no conandata.yml) — avoids the CI
    # build_and_test.sh "Pre-download" BUILD_DIR crash.
    exports_sources = "patches/*"

    def requirements(self):
        # afnix has no external library dependencies (ncurses/terminfo disabled on OHOS)
        pass

    def source(self):
        # Source url/sha256 hardcoded here (no conandata.yml) to avoid the CI
        # build_and_test.sh "Pre-download" stage crashing on an unset BUILD_DIR
        # variable. See commits 9b4660e5cf (iso-codes) / 1d55a9cccc (xmodem).
        get(
            self,
            url="http://www.afnix.org/ftp/afnix-src-3.8.0.tgz",
            sha256="63a8e7e0dc8670a548531d7a78a7922282f6dd10c5fc4526f9c1821e1928c8f4",
            strip_root=True,
        )

    def generate(self):
        # afnix uses its own afnix-setup; no AutotoolsToolchain needed
        pass

    def build(self):
        # Patches applied manually (no conandata.yml) — the patch files live
        # under patches/ in the recipe root, exported via exports_sources.
        for p in (
            "patches/0001-cnf_bin_afnix-guess.patch",
            "patches/0002-cnf_bin_afnix-vcomp.patch",
            "patches/0003-cnf_mak_afnix-cc13.mak.patch",
            "patches/0004-cnf_mak_afnix-libs.mak.patch",
            "patches/0005-src_lib_plt_shl_cthr.hxx.patch",
            "patches/0006-src_lib_plt_shl_ctrm.hxx.patch",
            "patches/0007-src_lib_std_shl_Regex.cpp.patch",
            "patches/0008-src_mod_nwg_shl_Basexx.cpp.patch",
        ):
            patch(self, patch_file=p)

        # afnix-setup configures the build tree (afnix has no ./configure)
        # Force clang compiler (afnix default is gcc; OHOS toolchain is clang)
        setup_cmd = [
            "./cnf/bin/afnix-setup",
            "--prefix={}".format(self.package_folder),
            "--ccname=clang",
        ]
        if self.options.shared:
            setup_cmd.append("--shared")
        else:
            setup_cmd.append("--static")
        self.run(" ".join(setup_cmd), env="conanbuild")

        # Build with make; OHOS_BUILD=1 skips libtinfo linkage on HarmonyOS
        # OHOS_FEATURE_NO_CANCEL/NO_TERM inject -DAFNIX_NO_CANCEL/-DAFNIX_NO_TERM
        # (build-time feature detection, not source platform macros — R8)
        self.run("make OHOS_BUILD=1 OHOS_FEATURE_NO_CANCEL=1 OHOS_FEATURE_NO_TERM=1 -j1", env="conanbuild")

    def package(self):
        # afnix install re-copies .so into bld/lib/ which HMDFS rejects on
        # overwrite (§7). Pre-clean bld/lib/*.so so the install cp succeeds.
        self.run("rm -f bld/lib/*.so bld/lib/*.so.* 2>/dev/null; true",
                 env="conanbuild")
        # Install to package_folder via PREFIX override
        self.run("make install PREFIX={} OHOS_BUILD=1 OHOS_FEATURE_NO_CANCEL=1 OHOS_FEATURE_NO_TERM=1".format(self.package_folder), env="conanbuild")

    def package_info(self):
        # afnix ships 24 libraries: plt, bit, std, eng, gfx, itu, mth, net,
        # nwg, sec, sio, sps, sys, tcz, tls, txt, wax, wgt, xml, xpe, svg,
        # bce, cda, dip, phy
        self.cpp_info.libs = [
            "afnix-plt", "afnix-bit", "afnix-std", "afnix-eng",
            "afnix-gfx", "afnix-itu", "afnix-mth", "afnix-net",
            "afnix-nwg", "afnix-sec", "afnix-sio", "afnix-sps",
            "afnix-sys", "afnix-tcz", "afnix-tls", "afnix-txt",
            "afnix-wax", "afnix-wgt", "afnix-xml", "afnix-xpe",
            "afnix-svg", "afnix-bce", "afnix-cda", "afnix-dip", "afnix-phy",
        ]
        # afnix libs depend on pthread, dl, m
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        # Library install layout: lib/libafnix-*.so, include/afnix/*/hdr.hpp
        self.cpp_info.includedirs = ["include/afnix"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
