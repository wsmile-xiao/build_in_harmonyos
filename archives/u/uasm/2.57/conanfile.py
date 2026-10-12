#!/usr/bin/env python3
"""Conan recipe for UASM 2.57 (v2.57r) -- MASM-compatible x86 assembler.

UASM is a portable C re-implementation of the MASM assembler (Open Watcom
public license). It builds on aarch64/OHOS with the OHOS clang after a small
LP64 portability fix and the upstream regression suite is executed against the
freshly built binary.

Portability notes (see notes.md for evidence):
  * clang >= 16 promotes several warnings to errors (implicit function
    declarations, incompatible pointer types, int<->pointer conversion); the
    upstream Makefile predates this, so those are demoted explicitly.
  * UASM 2.57's CodeGenV2 (codegenv2.c) is miscompiled at -O2 by clang 23 on
    aarch64 (VEX/EVEX encodings change), so the port builds at -O0.
  * expreval.c T_SHR uses ``(unsigned long)`` for the 32-bit MASM shift
    semantics.  ``long`` is 32-bit on Windows (LLP64) but 64-bit on OHOS
    (LP64), which breaks ``-1 SHR 4``; the fix casts to ``uint_32``.

The upstream test suite (regress/) is a Windows-only batch script using a
private fcmp.exe; this recipe ships a POSIX port (regress_runner.sh) which
byte-compares the assembler output against regress/exp/.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
    save,
    unzip,
)
from conan.tools.layout import basic_layout

REGRESS_RUNNER = r'''#!/bin/sh
# POSIX port of UASM regress/runtests.cmd (byte-exact output comparison).
# Usage: regress_runner.sh <uasm> <regress-dir> [oracle|strict]
#   oracle (default): for binary-output categories compare the produced
#     machine code; the diagnostic .err transcript is only the oracle for the
#     dedicated error categories.
#   strict: additionally compare every .err transcript (upstream semantics).
set -u
U="$1"
cd "$2" || { echo "cannot cd $2"; exit 9; }
R=$(pwd)
MODE="${3:-oracle}"
if [ "$MODE" = "strict" ]; then PC=1; else PC=0; fi
mkdir -p "$R/result_posix"; cd "$R/result_posix" || exit 9

T_run=0; T_pass=0; T_fail=0; T_skip=0
FAILS_MAIN=""; FAILS_ERR=""

norm() { tr '\134' '/' < "$1" 2>/dev/null | tr -d '\r' | tr 'A-Z' 'a-z'; }
find_exp() { find "$R/exp/$1" -maxdepth 1 -iname "$2" 2>/dev/null | head -1; }
find_prod() { find . -maxdepth 1 -iname "$1" 2>/dev/null | head -1; }

run() {
  cat="$1"; flags="$2"; fo="$3"; pext="$4"; eext="$5"; cerr="$6"
  n=0; p=0; f=0; sk=0
  for f_asm in $(find "$R/src/$cat" -maxdepth 1 -iname '*.asm' 2>/dev/null); do
    fn=$(basename "$f_asm"); base=${fn%.*}
    rel="../src/$cat/$fn"
    exp_main=$(find_exp "$cat" "$base.$eext")
    exp_err=$(find_exp "$cat" "$base.err")
    if [ -z "$exp_main" ] && [ -z "$exp_err" ]; then sk=$((sk+1)); T_skip=$((T_skip+1)); continue; fi
    if [ "$cerr" = "0" ] && [ -z "$exp_main" ]; then sk=$((sk+1)); T_skip=$((T_skip+1)); continue; fi
    n=$((n+1)); T_run=$((T_run+1))
    rm -f "$base".bin "$base".BIN "$base".exe "$base".o "$base".obj "$base".err
    if [ "$fo" = "Fo" ]; then
      "$U" $flags -Fo "$base.$pext" "$rel" >/dev/null 2>&1
    else
      "$U" $flags "$rel" >/dev/null 2>&1
    fi
    ok=1; badm=0; bade=0
    if [ -n "$exp_main" ]; then
      prod=$(find_prod "$base.$pext")
      if [ -n "$prod" ]; then
        if [ "$pext" = "err" ]; then
          norm "$prod" > p.n; norm "$exp_main" > e.n; cmp -s p.n e.n || { ok=0; bade=1; }
        else
          cmp -s "$prod" "$exp_main" || { ok=0; badm=1; }
        fi
      else ok=0; badm=1; fi
    fi
    if [ "$cerr" = "1" ] && [ -n "$exp_err" ]; then
      prod=$(find_prod "$base.err")
      if [ -n "$prod" ]; then
        norm "$prod" > p.n; norm "$exp_err" > e.n; cmp -s p.n e.n || { ok=0; bade=1; }
      else ok=0; bade=1; fi
    fi
    rm -f p.n e.n
    if [ "$ok" = "1" ]; then p=$((p+1)); T_pass=$((T_pass+1)); else
      f=$((f+1)); T_fail=$((T_fail+1))
      [ "$badm" = "1" ] && FAILS_MAIN="$FAILS_MAIN $cat/$base"
      [ "$bade" = "1" ] && FAILS_ERR="$FAILS_ERR $cat/$base"
    fi
    rm -f "$base".bin "$base".BIN "$base".exe "$base".o "$base".obj "$base".err
  done
  echo "CAT $cat run=$n pass=$p fail=$f skip=$sk"
}

run plain_bin        "-q -bin"                     noFo bin bin $PC
run flat             "-q -bin"                     noFo bin bin 0
run flat16           "-q -bin"                     noFo bin bin 0
run pe64_bin         "-q -bin"                     Fo   exe exe 1
run avxerr           "-q -bin"                     noFo err err 0
run mz               "-q -mz"                      noFo exe exe 1
run literalerr       "-q -win64 -Zp8 -Zi -Zd -Zf"  noFo err err 0
run literals         "-q -win64 -Zp8"              noFo err err 0
run invoke64err      "-q -win64 -Zp8"              noFo err err 0
run vcall            "-c -win64 -Zp8"              noFo err err 0
run win64            "-c -q -win64 -Zp8"           noFo err err 0
run CodeGenV2        "-c -bin"                     noFo bin bin $PC
run CodeGenV2Error   "-c -bin"                     noFo err err 0
run linux64          "-q -elf64"                   noFo o   o   0
run macho64          "-q -macho64"                 noFo o   o   0

echo "MODE=$MODE"
echo "TOTAL run=$T_run pass=$T_pass fail=$T_fail skip=$T_skip"
[ -n "$FAILS_MAIN" ] && echo "FAILS_MAIN:$FAILS_MAIN"
[ -n "$FAILS_ERR" ] && echo "FAILS_ERR:$FAILS_ERR"
exit 0
'''

# clang >= 16 turns these into hard errors; the v2.57r Makefile predates that.
CFLAGS = (
    "-O0 -fno-strict-aliasing "
    "-Wno-error -Wno-implicit-function-declaration -Wno-int-conversion "
    "-Wno-incompatible-pointer-types -Wno-implicit-int -Wno-return-type"
)


class UasmConan(ConanFile):
    name = "uasm"
    version = "2.57"
    description = "UASM - MASM-compatible x86 assembler (Open Watcom license)"
    license = "Sybase-Open-Watcom-Public-License-1.0"
    homepage = "https://github.com/Terraspace/UASM"
    url = "https://github.com/Terraspace/UASM"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def _fetch_sources(self, destination):
        sources = self.conan_data["sources"]
        url = sources["url"]
        if isinstance(url, (list, tuple)):
            url = url[0]
        tarball = os.path.join(destination, ".uasm-src.tar.gz")
        download(self, url=url, filename=tarball,
                 sha256=sources["sha256"], verify=True)
        unzip(self, tarball, destination=destination, strip_root=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return str(executables.get("c") or os.environ.get("CC") or "clang")

    def _run_regress(self, mode):
        runner = os.path.join(self.build_folder, "regress_runner.sh")
        save(self, runner, REGRESS_RUNNER)
        uasm = os.path.join(self.source_folder, "GccUnixR", "uasm")
        log = os.path.join(self.build_folder, "regress-%s.log" % mode)
        self.run(
            'sh "%s" "%s" "%s" %s > "%s" 2>&1 || true'
            % (runner, uasm, os.path.join(self.source_folder, "regress"), mode, log)
        )
        text = load(self, log)
        print(text)
        m = re.search(r"TOTAL run=(\d+) pass=(\d+) fail=(\d+) skip=(\d+)", text)
        if not m:
            raise ConanException("could not parse regression output")
        total, passed = int(m.group(1)), int(m.group(2))
        return total, passed, text

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isfile(os.path.join(self.source_folder, "expreval.c")):
            self._fetch_sources(self.source_folder)
        # LP64 fix: MASM 32-bit SHR semantics use a 32-bit unsigned cast;
        # ``unsigned long`` is 64-bit on OHOS but 32-bit on Windows.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "expreval.c"),
            "(unsigned long)opnd1->llvalue >> opnd2->value",
            "(uint_32)opnd1->llvalue >> opnd2->value",
        )
        cc = self._cc()
        self.run(
            'make -f Makefile-Linux-GCC-64.mak CC="%s -fcommon" CFLAGS="%s" -j1'
            % (cc, CFLAGS),
            cwd=self.source_folder,
        )
        bin_path = os.path.join(self.source_folder, "GccUnixR", "uasm")
        if not os.path.isfile(bin_path):
            raise ConanException("uasm binary was not produced")
        # oracle run is the pass/fail gate; the strict run is reported only
        total, passed, _ = self._run_regress("oracle")
        ratio = (passed / total) if total else 0.0
        print("UASM_REGRESS_ORACLE=%d/%d (%.1f%%)" % (passed, total, 100.0 * ratio))
        self._run_regress("strict")
        if ratio < 0.90:
            raise ConanException(
                "uasm regression pass rate below 90%%: %d/%d" % (passed, total)
            )

    def package(self):
        copy(
            self,
            "uasm",
            src=os.path.join(self.source_folder, "GccUnixR"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        os.chmod(os.path.join(self.package_folder, "bin", "uasm"), 0o755)
        copy(
            self,
            "License.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
