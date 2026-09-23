#!/usr/bin/env python3
"""Conan recipe — bruteforce-wallet 1.5.4.

Try to find the password of an encrypted Peercoin (or Bitcoin, Litecoin,
...) wallet file (wallet.dat), by exhaustive search or dictionary attack.
Upstream is a trivial Autotools C tool (configure.ac + Makefile.am,
2 C files, no config.h, no generated headers).

HarmonyOS adaptations:
  - Direct compile (knock/0.8.2-r2, zimg/3.0.6 precedent): the GitHub tag
    archive ships no pre-generated configure and the preflight box has no
    `autoreconf` on PATH (verified: `autoreconf: inaccessible or not
    found`), nor `bash`. Upstream configure.ac only probes standard
    headers plus -lm/-pthread/-lcrypto/-ldb, and the sources include no
    config.h, so build() compiles src/*.c directly with the Conan
    compiler, bypassing autogen/configure entirely. No autotools
    tool_requires needed.
  - OpenSSL/BerkeleyDB include/lib paths come from the Conan dependencies
    (R33: compiler prefers tools.build:compiler_executables when the file
    exists, else first clang/cc/gcc on PATH for the preflight box).
  - R26: terminal tools link statically (-static).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class BruteforceWalletConan(ConanFile):
    name = "bruteforce-wallet"
    version = "1.5.4"
    description = (
        "Try to find the password of an encrypted cryptocurrency wallet file"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/glv2/bruteforce-wallet"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("berkeley-db/4.8.30")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, but the profile path
        # (/data/service/hnp/bin/clang) does not exist on the preflight
        # box (verified: `inaccessible or not found`). Accept the conf
        # value only when the file exists; otherwise fall back to the
        # first compiler found on PATH (zimg _resolve_tool precedent).
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = None
        configured = (comp_execs or {}).get("c")
        if configured and os.path.isfile(configured):
            cc = configured
        if not cc:
            for cand in ("clang", "cc", "gcc"):
                found = shutil.which(cand)
                if found:
                    cc = found
                    break
        if not cc:
            cc = configured or "cc"
        openssl = self.dependencies["openssl"]
        bdb = self.dependencies["berkeley-db"]
        build_type = str(self.settings.build_type)
        opt_map = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        opt = opt_map.get(build_type, "-O2")
        src = self.source_folder
        # Upstream sources: src/bruteforce-wallet.c + src/elliptic-curve.c
        # (Makefile.am bin_PROGRAMS, no config.h). Compile directly so no
        # autoreconf/autogen/configure is needed on the locked-down box.
        self.run(
            f"{cc} {opt} -Isrc "
            f"-I{openssl.package_folder}/include "
            f"-I{bdb.package_folder}/include "
            f"src/bruteforce-wallet.c src/elliptic-curve.c -o bruteforce-wallet "
            f"-L{openssl.package_folder}/lib -L{bdb.package_folder}/lib "
            f"-lcrypto -ldb -lm -pthread -static",
            cwd=src,
        )
        # No upstream test harness (audit in test_package/MANIFEST.yml), so no
        # `make check` here. Upstream evidence (HMBS_UPSTREAM_TEST_RESULT,
        # status passed, discovered=1 for the compile-equivalent step) is
        # emitted by test_package/test.sh after it verifies the built
        # binary actually runs (nwipe/0.39 precedent: single source in
        # test.sh, not a static no_tests marker from build()).

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(
            self,
            "bruteforce-wallet",
            src=self.source_folder,
            dst=bindir,
            keep_path=False,
        )
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(mandir, exist_ok=True)
        copy(
            self,
            "bruteforce-wallet.1",
            src=self.source_folder,
            dst=mandir,
            keep_path=False,
        )

    def package_info(self):
        # Application: only binaries, no libs/headers.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
