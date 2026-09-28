#!/usr/bin/env python3
"""Conan recipe for simh 3.8.1 — SIMH multi-system historical computer simulator.

SIMH V3.8-1 (Robert M Supnik, 2009-02-08) emulates a family of historic
computers (PDP-1/4/7/8/9/10/11/15, VAX/VAX-11/780, Nova/Eclipse, HP 2100,
IBM 1401/1620/7094/1130, Altair 8800/AltairZ80, GRI-909, SDS, LGP-30, H316,
Interdata 16/32, Scientific Data Systems S3, ...) as a set of standalone
command-line emulator binaries.

Debian/derivative distros package this tarball as version 3.8.1 (upstream
revision V3.8-1); the Conan package version follows that convention.

Build system: hand-written GNU makefile (no autotools/cmake, no install target,
no unit-test suite). The makefile hardcodes `CC = gcc -std=c99
-U__STRICT_ANSI__ -g $(OS_CCDEFS) -I .` where OS_CCDEFS = `-lrt -lm
-D_GNU_SOURCE`, so we override CC/LDFLAGS on the make command line to target
OHOS (clang + musl):

  - CC: clang (musl folds librt into libc, so -lrt is dropped)
  - -lm is passed via LDFLAGS so it lands after the object list (link order)
  - -D_GNU_SOURCE is kept: musl exposes the few extensions simh uses
    (strncasecmp/usleep) only under it
  - -fcommon restores the pre-C99 common-symbol merging this 1993-2009 code
    relies on (clang >= 15 defaults to -fno-common; see notes.md)

The upstream `all` target builds 26 emulators (an `i1620` typo makes it appear
twice in the makefile's ALL list; the distinct set is 26). There is no upstream
test suite, so build() runs the real upstream build and test_package verifies
the *installed* binaries start and dispatch the SCP command interpreter.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout

# The 26 emulator executables produced by the upstream default "all" target
# (unique set; the makefile's ALL list repeats i1620, which dedupes to 26).
SIMH_BINS = (
    "altair", "altairz80", "eclipse", "gri", "h316", "hp2100", "i1401",
    "i1620", "i7094", "ibm1130", "id16", "id32", "lgp", "nova", "pdp1",
    "pdp10", "pdp11", "pdp15", "pdp4", "pdp7", "pdp8", "pdp9", "s3", "sds",
    "vax", "vax780",
)

# OHOS code-signing tooling. The DEVICE/CI provides binary-sign-tool; on a
# plain Linux/Windows host we skip signing and let the packaged consumer sign
# (HarmonyOS PC refuses to exec unsigned ELF, so signing is best-effort here).
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
)
_OBJCOPY_CANDIDATES = (
    "/data/service/hnp/bin/llvm-objcopy",
    "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
)

_LICENSE_TEXT = """\
Copyright (c) 1993-2009, Robert M Supnik

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL ROBERT
M SUPNIK BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Except as contained in this notice, the name of Robert M Supnik shall not be
used in advertising or otherwise to promote the sale, use or other dealings in
this Software without prior written authorization from Robert M Supnik.

(This text is reproduced from the per-file header of the upstream source,
e.g. scp.c / sim_rev.h; the V3.8-1 tarball ships no standalone LICENSE file.)
"""


class SimhConan(ConanFile):
    name = "simh"
    version = "3.8.1"
    description = (
        "SIMH historical computer simulator (V3.8-1): 26 standalone emulators "
        "for PDP-1/4/7/8/9/10/11/15, VAX/VAX-11/780, Nova/ECLIPSE, HP 2100, "
        "IBM 1401/1620/7094/1130, Altair 8800/AltairZ80, GRI-909, SDS, "
        "LGP-30, H316, Interdata 16/32 and Scientific Data Systems S3."
    )
    license = "MIT"
    homepage = "http://simh.trailing-edge.com/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "simh/3.8.1 in this recipe targets HarmonyOS PC (OHOS)/Linux only"
            )

    def source(self):
        # Source URL/SHA256 live in conandata.yml. The archive is a ZIP with
        # 44 top-level entries (no single root dir), so strip_root=False.
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        # R33: take the compiler from Conan conf, never from bare shell vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        # The makefile treats CC as the full compile command (`CC = gcc ...`),
        # so a command-line CC override replaces gcc + its hardcoded -lrt -g.
        # -fcommon: simh V3.8-1 relies on GCC's historic common-symbol merging
        # (altairz80's `intr`, ibm1130's `sim_vm_init` are tentative
        # definitions); clang defaults to -fno-common and lld then reports
        # duplicate symbols (verified locally, see notes.md).
        cc_cmd = f"{cc} -std=c99 -U__STRICT_ANSI__ -O2 -D_GNU_SOURCE -fcommon -I."
        # The upstream source zip carries an empty BIN/ directory, which zip
        # extraction drops; the makefile writes emulators into BIN/ without
        # creating it, so create it explicitly before linking.
        os.makedirs(os.path.join(self.source_folder, "BIN"), exist_ok=True)
        # R9: always -j1. LDFLAGS puts -lm after the object list (link order).
        self.run(
            f'make CC="{cc_cmd}" LDFLAGS="-lm" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.source_folder, "BIN")
        dst = os.path.join(self.package_folder, "bin")
        os.makedirs(dst, exist_ok=True)
        missing = []
        for exe in SIMH_BINS:
            src = os.path.join(bin_dir, exe)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst, exe))
            else:
                missing.append(exe)
        if missing:
            raise ConanException(
                "simh: emulator(s) missing from BIN/ after build: %s" % ", ".join(missing)
            )
        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        with open(os.path.join(self.package_folder, "licenses", "LICENSE"), "w") as fh:
            fh.write(_LICENSE_TEXT)
        self._sign_binaries()

    def _sign_binaries(self):
        """Self-sign the OHOS ELF executables (HarmonyOS MAC refuses unsigned).

        Best-effort: the signing tools only exist on the device/CI runner. On a
        plain Linux/Windows host we skip and let the packaged consumer re-sign.
        """
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = next(
            (p for p in (shutil.which("binary-sign-tool"), *_SIGN_TOOL_CANDIDATES)
             if p and os.path.exists(p)),
            None,
        )
        objcopy = next(
            (p for p in (shutil.which("llvm-objcopy"), *_OBJCOPY_CANDIDATES)
             if p and os.path.exists(p)),
            None,
        )
        if not sign_tool:
            self.output.warning(
                "binary-sign-tool not found; skipping OHOS ELF self-signing "
                "(consumer must re-sign)"
            )
            return
        bindir = os.path.join(self.package_folder, "bin")
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if objcopy:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    capture_output=True,
                )
            res = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
                capture_output=True,
            )
            if res.returncode != 0:
                self.output.warning(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (name, res.returncode, res.stderr.decode(errors="replace")[:200])
                )
            else:
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
