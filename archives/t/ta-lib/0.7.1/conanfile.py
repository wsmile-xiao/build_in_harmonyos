#!/usr/bin/env python3
"""Conan recipe for ta-lib 0.7.1 — OHOS PC (aarch64) adaptation.

TA-Lib is a pure-C technical analysis library for financial markets
(~200 indicator functions: SMA/EMA/MACD/RSI/Stochastic/Bollinger/
candlestick patterns, ...).  0.7.x is the new-generation upstream
(github.com/ta-lib/ta-lib), not the old 0.6.x SourceForge line.

Build system (simple autotools, zero external deps — only libm):
  * the v0.7.1 release tarball ships a pre-generated `configure`,
    so no autogen/automake bootstrap is needed;
  * configure is run in-tree with explicit --build/--host=
    aarch64-unknown-linux-ohos because the bundled 2022-era
    config.guess cannot identify HarmonyOS and the bundled
    config.sub rejects `ohos` (patch 0001 adds `ohos*` /
    `linux-ohos*` to config.sub);
  * in-tree is required: upstream Makefile.am hard-codes relative
    include paths (-I../../include, -I../../ta_func, ...) that only
    resolve when make runs inside the source tree — a VPATH build
    dies on ta_def_ui.h's #include "ta_abstract.h";
  * make runs with -j1 (E074: HMDFS has no jobserver fifo support).

HMDFS notes:
  * E114 hit in the conan cache (HMDFS): config.status dies on
    ./confXXXXXX/subs1.awk "Permission denied" because the temp dir
    comes from `umask 077 && mktemp -d` — the umask is stripped from
    both spots in build() (codecrypt 1.8 / objfw 1.5.7 precedent);
    note it did NOT trigger on the $TMPDIR explore build — the
    difference is the filesystem, not the tarball;
  * `make install` rewrites RPATH on installed shared libs; the
    package() step stages via DESTDIR once and copies artifacts
    byte-identically to keep OHOS fs-verity code signatures valid
    (same approach as the litecoin recipe).

Upstream regression tests (src/tools/ta_regtest, noinst) are built
with the library and executed in build() — pure math functions run
fine on the device (all tests succeeded locally).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (copy, get, apply_conandata_patches,
                              export_conandata_patches, replace_in_file)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TaLibConan(ConanFile):
    name = "ta-lib"
    version = "0.7.1"
    description = ("TA-Lib: technical analysis library with ~200 "
                   "financial market indicator functions (pure C)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/ta-lib/ta-lib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ta-lib is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        # source == build: in-tree autotools (upstream Makefile.am
        # relative -I paths only resolve inside the source tree)
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # tarball extracts ./configure with -rwxrwx--- (group bit only);
        # the CI user is not in that group (E126) — chmod 0o755 first
        os.chmod(os.path.join(self.source_folder, "configure"), 0o755)

    def _configure_args(self):
        args = [
            # config.guess (2022-01-09) cannot identify HarmonyOS; pass
            # the triplet explicitly so the guess probe never runs.
            # config.sub accepts *-linux-ohos after patch 0001.
            "--build=aarch64-unknown-linux-ohos",
            "--host=aarch64-unknown-linux-ohos",
            # fixed prefix: package() installs with DESTDIR=<staging> and
            # the artifacts land under <staging>/usr/local — copied from
            # there into the conan package folder
            "--prefix=/usr/local",
        ]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
        return args

    def generate(self):
        tc = AutotoolsToolchain(self)
        for arg in self._configure_args():
            tc.configure_args.append(arg)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E114: the config.status template in `configure` creates its
        # temp dir via `umask 077 && mktemp -d`; on HMDFS (the conan
        # cache lives there) the resulting 0700 dir is unwritable even
        # by its owner and config.status dies with
        #   ./confXXXXXX/subs1.awk: Permission denied
        # Drop the umask from both the mktemp branch and the mkdir
        # fallback (codecrypt 1.8 / objfw 1.5.7 precedent).
        _conf = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, _conf,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        replace_in_file(
            self, _conf,
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"')
        # In-tree configure + make (upstream Makefile.am hard-codes
        # relative -I paths; VPATH build dies on ta_abstract.h).
        src = self.source_folder
        conf_args = " ".join(self._configure_args())
        self.run(f'cd "{src}" && ./configure {conf_args}', env="conanbuild")
        # R9/E074: single job — parallel make hits HMDFS jobserver fifo EPERM
        self.run(f'cd "{src}" && make -j1', env="conanbuild")
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream regression test suite (ta_regtest).

        ta_regtest is a noinst binary under src/tools/ta_regtest that
        validates every TA function family (math/vector, moving
        averages, aroon/correl/beta/midprice, cci/willr/ultosc/natr,
        bop/avgprice, rsi/cmo, imi, min/max family, po/apo, adx family,
        sar, stoch family, mfi/ad, phasor/sine, trix, macd family,
        mom family, trange/atr, stddev/var, avgdev, bbands, period
        boundary, all candlesticks) against reference data
        (ta_gData*.c).  Pure math — runs fine on the device host.
        """
        if not can_run(self):
            self.output.info(
                "upstream ta_regtest skipped: cannot run target binaries "
                "on the build host (cross build)")
            return
        regtest = os.path.join(
            self.source_folder, "src", "tools", "ta_regtest",
            ".libs", "ta_regtest")
        if not os.path.isfile(regtest):
            regtest = os.path.join(
                self.source_folder, "src", "tools", "ta_regtest",
                "ta_regtest")
        if not os.path.isfile(regtest):
            raise RuntimeError("ta_regtest binary not found after make")
        # ta_regtest links the just-built libta-lib.so; point the loader
        # at the un-installed .libs/ directory.
        libdir = os.path.join(self.source_folder, "src", ".libs")
        self.run(
            f'export LD_LIBRARY_PATH="{libdir}:$LD_LIBRARY_PATH"; '
            f'"{regtest}"', env="conanbuild")

    def package(self):
        # Stage via DESTDIR once, then copy byte-identically: a second
        # `make install` would rewrite RPATH on the shared libs and
        # invalidate OHOS fs-verity code signatures (litecoin recipe
        # precedent).  DESTDIR + --prefix=<package_folder> nests the
        # artifacts under <staging>/<package_folder>/.
        pkg = self.package_folder
        staging = os.path.join(self.build_folder, "package-staging")
        staged_prefix = os.path.join(staging, "usr", "local")
        self.run(
            f'cd "{self.source_folder}" && make install DESTDIR="{staging}"',
            env="conanbuild")
        copy(self, "*", src=os.path.join(staged_prefix, "include"),
             dst=os.path.join(pkg, "include"), keep_path=True)
        copy(self, "*", src=os.path.join(staged_prefix, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=True)
        # .la files are libtool metadata (conan owns dependency info)
        for la in os.listdir(os.path.join(pkg, "lib")):
            if la.endswith(".la"):
                os.remove(os.path.join(pkg, "lib", la))
        # LICENSE
        for lic in ("LICENSE", "LICENSE.txt", "COPYING"):
            cand = os.path.join(self.source_folder, lic)
            if os.path.isfile(cand):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(pkg, "licenses"))
                break

    def package_info(self):
        self.cpp_info.libs = ["ta-lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "ta-lib")
        self.cpp_info.set_property("cmake_target_name", "ta-lib::ta-lib")
        self.cpp_info.set_property("pkg_config_name", "ta-lib")
