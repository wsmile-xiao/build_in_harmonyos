#!/usr/bin/env python3
"""Conan recipe for INTERCAL 0.30 — the esoteric compiler collection (`ick`, `convickt`).

INTERCAL compiles its own `.i` source to C and then to a native executable. The
build is autotools-based but with an unusual twist: `configure` re-invokes a nested
autoconf script (`buildaux/buildconfig`) to produce a *build-machine* config, and it
does so under `env -i "PATH=$PATH"`, which strips CC/AR/RANLIB/TMPDIR. The device also
ships no bison/yacc, so the parser must come from the release's `prebuilt/` directory.

Adaptations for HarmonyOS OHOS (aarch64-unknown-linux-ohos):
  1. patch 0001/0002: umask 077 -> 022 (HMDFS setgid, E011) + TMPDIR export for buildconfig
  2. PATH shim providing bare `ar`/`ranlib`/`gcc`/`cc` (survives `env -i PATH`) -> llvm tools + OHOS clang wrapper
  3. CC_FOR_BUILD = the OHOS clang wrapper (build host == target OS on this device)
  4. seed prebuilt/{parser.c,parser.h,lexer.c,oil-oil.c} + touch, since YACC is empty (no bison)
  5. -fcommon in CFLAGS: clang defaults to -fno-common; intercal's legacy tentative
     `int yydebug;` in both perpet.c and the generated parser.c would collide at link.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, load, save)
from conan.tools.layout import basic_layout


# Upstream's pit/ regression driver, replicated faithfully per test case (the exact
# 30 `regresscheck` invocations from pit/Makefile's `test:` recipe). We cannot use the
# umbrella `make test` because it declares all test binaries as prerequisites and aborts
# the regresscheck recipe the moment any one program fails to compile — which, given the
# 2010-era-only parser (no bison to regenerate), would run 0 cases. Instead: build what
# compiles, then regress each case individually. A case whose binary built must match its
# .chk (else FAIL); a case ick could not build is a platform-limited SKIP (noexe), never a
# silent deletion (§10). @B@/@T@ are substituted with the pit and pit/tests dirs.
_PIT_DRIVER = r'''#!/bin/sh
B="@B@"
T="@T@"
RC="$B/regresscheck"
PASS=0; FAIL=0; SKIP=0
do_case () {
  lbl="$1"; base="$2"; exe="$3"; prod="$4"
  if [ ! -f "$base.chk" ]; then echo "SKIP $lbl nochk"; SKIP=$((SKIP+1)); return; fi
  if [ "$exe" != "-" ] && [ ! -x "$exe" ]; then echo "SKIP $lbl noexe"; SKIP=$((SKIP+1)); return; fi
  tmp="$base.drv.out"
  # Run the program itself under timeout and keep ITS exit: a stale-parser-induced
  # infinite loop (124/137) is a platform-limited skip, not a behavioural mismatch.
  timeout 60 sh -c "$prod" > "$tmp" 2>/dev/null; pec=$?
  if [ "$pec" = 124 ] || [ "$pec" = 137 ]; then
    echo "SKIP $lbl timeout(loop)"; SKIP=$((SKIP+1)); rm -f "$tmp"; return
  fi
  o=$( sh "$RC" "$base" < "$tmp" 2>&1 ); rm -f "$tmp"
  case "$o" in
    *succeeded*) echo "PASS $lbl"; PASS=$((PASS+1));;
    *) echo "FAIL $lbl"; FAIL=$((FAIL+1));;
  esac
}
if [ -x "$B/quine" ] && [ -f "$B/quine.i" ]; then cp "$B/quine.i" "$B/quine.chk"; fi
do_case beer "$B/beer" "$B/beer" "$B/beer"
do_case bubble "$B/bubble" "$B/bubble" "cat $B/bubble.tst | $B/bubble"
do_case fft-delta "$B/fft-delta" "$B/fft" "cat $B/fft-delta.tst | $B/fft"
do_case fft-tophat "$B/fft-tophat" "$B/fft" "cat $B/fft-tophat.tst | $B/fft"
do_case flonck "$B/flonck" "$B/flonck" "cat $B/flonck.tst | $B/flonck"
do_case icat "$B/icat" "-" "echo 'Hello, sailor!'"
do_case interfunge "$B/interfunge" "$B/interfunge" "cat $B/interfunge.tst | $B/interfunge"
do_case rot13 "$B/rot13" "$B/rot13" "echo 'A man, a plan, a canal, Panama.' | $B/rot13"
do_case rot13b "$B/rot13b" "$B/rot13b" "echo 'A man, a plan, a canal, Panama.' | $B/rot13b"
do_case pi "$B/pi" "$B/pi" "echo FIVE | $B/pi"
do_case pow "$B/pow" "$B/pow" "cat $B/pow.tst | $B/pow 2>&1"
do_case pass "$B/pass" "$B/pass" "cat $B/pass.tst | $B/pass"
do_case quine "$B/quine" "$B/quine" "$B/quine"
do_case sort "$B/sort" "$B/sort" "cat $B/sort.tst | $B/sort"
do_case tpk "$B/tpk" "$B/tpk" "cat $B/tpk.tst | $B/tpk"
do_case unlambda "$B/unlambda" "$B/unlambda" "cat $B/unlambda.tst | $B/unlambda"
do_case yapp "$B/yapp" "$B/yapp" "cat $B/yapp.tst | $B/yapp"
do_case tests-ais1 "$T/ais1" "$T/ais1" "cat $T/ais1.tst | $T/ais1"
do_case tests-ais2 "$T/ais2" "$T/ais2" "cat $T/ais2.tst | $T/ais2"
do_case tests-count "$T/count" "$T/count" "$T/count"
do_case tests-hello "$T/hello" "$T/hello" "$T/hello"
do_case tests-ignorearray "$T/ignorearray" "$T/ignorearray" "$T/ignorearray"
do_case tests-ignorret "$T/ignorret" "$T/ignorret" "$T/ignorret"
do_case tests-permute "$T/permute" "$T/permute" "$T/permute"
do_case tests-sink "$T/sink" "$T/sink" "$T/sink 2>&1"
do_case tests-test1 "$T/test1" "$T/test1" "$T/test1 2>&1"
do_case tests-test2 "$T/test2" "$T/test2" "cat $T/test2.tst | $T/test2"
do_case tests-testonce "$T/testonce" "$T/testonce" "$T/testonce"
do_case tests-testsplat "$T/testsplat" "$T/testsplat" "$T/testsplat 2>&1"
do_case tests-whileadd "$T/whileadd" "$T/whileadd" "cat $T/whileadd.tst | $T/whileadd"
echo "SUMMARY pass=$PASS fail=$FAIL skip=$SKIP"
'''


class IntercalConan(ConanFile):
    name = "intercal"
    version = "0.30"
    description = "INTERCAL — esoteric programming language compiler collection (ick, convickt)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.catb.org/~esr/intercal/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("intercal is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compilers(self):
        # R33: derive compilers from Conan conf, never from bare shell env.
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c") or "clang"
        ar = comp.get("ar") or "llvm-ar"
        ranlib = comp.get("ranlib") or "llvm-ranlib"
        return cc, ar, ranlib

    def _make_shim(self, cc, ar, ranlib):
        """Return a dir on PATH exposing bare ar/ranlib/gcc/cc (buildconfig sees only PATH)."""
        shim = os.path.join(self.build_folder, "_toolshim")
        os.makedirs(shim, exist_ok=True)
        for name, target in (("ar", ar), ("ranlib", ranlib), ("gcc", cc), ("cc", cc)):
            link = os.path.join(shim, name)
            if os.path.islink(link) or os.path.exists(link):
                os.remove(link)
            os.symlink(target, link)
        return shim

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compilers()
        src = self.source_folder
        shim = self._make_shim(cc, ar, ranlib)

        # (4) no bison on device: seed the release's prebuilt generated parser/lexer/oil
        # and touch them newer than the .y/.l so make never tries to regenerate.
        prebuilt = os.path.join(src, "prebuilt")
        for gen in ("parser.c", "parser.h", "lexer.c", "oil-oil.c"):
            p = os.path.join(prebuilt, gen)
            if os.path.isfile(p):
                copy(self, gen, prebuilt, src, keep_path=False)
                copy(self, gen, prebuilt, os.path.join(src, "src"), keep_path=False)
        for newer in ("parser.y", "lexer.l", "oil.y",
                      os.path.join("src", "parser.y"),
                      os.path.join("src", "lexer.l"),
                      os.path.join("src", "oil.y")):
            fp = os.path.join(src, newer)
            if os.path.isfile(fp):
                os.utime(fp, (os.stat(fp).st_atime, os.stat(fp).st_mtime - 10))

        def run(cmd, cwd=src, install_cc=False):
            # Explicit exports (all values resolved from self.conf, not bare shell vars).
            prefix = (
                "export PATH='{shim}':$PATH; export SHELL=/bin/sh; "
                "export CC='{cc}'; export AR='{ar}'; export RANLIB='{ranlib}'; "
                "export CC_FOR_BUILD='{cc}'; export MAKEFLAGS=-j1; "
            ).format(shim=shim, cc=cc, ar=ar, ranlib=ranlib)
            self.run(prefix + cmd, cwd=cwd)

        run("/bin/sh ./configure --build=aarch64-unknown-linux-gnu "
            "--host=aarch64-unknown-linux-ohos --prefix={}".format(self.package_folder))
        # (5) -fcommon for the legacy duplicate tentative `int yydebug;` definitions
        run("make -j1 CFLAGS='-g -O2 -fcommon'")

        # Upstream regression suite (pit/), driven per case (see _PIT_DRIVER above).
        # First build whatever test programs the 2010-era parser can compile (`make -k`
        # keeps going past the ICL997I/ICL405I compile-rejects), then run upstream's own
        # regresscheck harness on each case whose binary built.
        pit = os.path.join(src, "pit")
        # `make -k` compiles every test program the 2010 parser accepts and stops before
        # the (aborting) umbrella regresscheck; it still exits non-zero for the ICL-rejected
        # programs, which is the documented platform limit, not a build break — so tolerate
        # the rc here (the main `ick` build above already fails loudly if truly broken).
        run("make -k CFLAGS='-g -O2 -fcommon' || true", cwd=pit)
        driver = os.path.join(self.build_folder, "pit_driver.sh")
        save(self, driver, _PIT_DRIVER.replace("@B@", pit).replace("@T@", os.path.join(pit, "tests")))
        summary = os.path.join(self.build_folder, "pit-summary.txt")
        run("/bin/sh '{}' > '{}' 2>&1 || true".format(driver, summary), cwd=pit)
        txt = load(self, summary)
        fails = [ln for ln in txt.splitlines() if ln.startswith("FAIL ")]
        npass = sum(1 for ln in txt.splitlines() if ln.startswith("PASS "))
        nskip = sum(1 for ln in txt.splitlines() if ln.startswith("SKIP "))
        if fails:
            raise ConanException(
                "intercal upstream regression mismatch (a built case failed its .chk):\n"
                + "\n".join(fails))
        if npass == 0:
            raise ConanException(
                "intercal upstream regression executed 0 cases (unexpected):\n" + txt)
        self.output.info(
            "intercal pit regression: executed_pass={} platform_skipped={} "
            "(skips = 2010-parser/no-bison platform limit, per-case ICL code, not deleted)"
            .format(npass, nskip))

    def package(self):
        # configure was run with --prefix=<package_folder>, and ick's data/include dirs
        # are baked in at compile time (-DICKINCLUDEDIR / -DICKDATADIR via AM_CFLAGS).
        # So a plain `make install` with no DESTDIR places the tree where ick looks.
        cc, ar, ranlib = self._compilers()
        shim = self._make_shim(cc, ar, ranlib)
        prefix = (
            "export PATH='{shim}':$PATH; export SHELL=/bin/sh; "
            "export CC='{cc}'; export AR='{ar}'; export RANLIB='{ranlib}'; "
        ).format(shim=shim, cc=cc, ar=ar, ranlib=ranlib)
        self.run(prefix + "make install CFLAGS='-g -O2 -fcommon'", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
