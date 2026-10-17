#!/usr/bin/env python3
"""Conan recipe for gputils 1.5.2 — GNU PIC Utilities (gpasm/gplink/gplib,
C tools, autotools, SourceForge source, zero deps).

Adaptation lessons applied:
- sdist ships no configure (Makefile.in only) — run autoreconf first.
- E007: config.guess cannot guess OHOS — pass --build/--host explicitly.
- E011: config.status temp-dir creation may hit Permission denied on
  hmdfs — set TMPDIR to the build staging dir (CI cache may differ).
- self.run env arg must be a list — use command-prefix env vars.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class GputilsConan(ConanFile):
    name = "gputils"
    version = "1.5.2"
    description = "GNU PIC Utilities — assembler/linker for PIC MCUs"
    license = "GPL-2.0"
    homepage = "https://gputils.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # config.status tmpdir must be on a writable (non-hmdfs) location.
        # conanbuild env sets TMPDIR=~/.cache/tmp (hmdfs — Permission
        # denied on config.status mkdir), NOT the CI process TMPDIR — so
        # hardcode the CI-writable /data/storage/el2/base/cache instead of
        # reading $TMPDIR (perl-family lesson).
        tmpdir = "/data/storage/el2/base/cache"
        os.makedirs(tmpdir, exist_ok=True)
        # sdist ships configure — skip autoreconf (aclocal is unexecutable
        # on CI: hmdfs forces 0o770, USER=100 has no perms — chmod is
        # ineffective there). Configure directly.
        bld = "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        # E011 fix (sdcc/GDB pattern): config.status tmpdir (ac_tmp) uses
        # `mktemp -d "./confXXXXXX"` + fallback `mkdir ./conf$$-$RANDOM` —
        # hmdfs blocks mkdir (Permission denied on ./confXXX/subs1.awk).
        # Patch configure BEFORE running it: ac_tmp must use $TMPDIR.
        _cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(_cfg):
            _s = open(_cfg).read()
            _s2 = _s.replace('mktemp -d "./confXXXXXX"',
                             'mktemp -d "$TMPDIR/confXXXXXX"')
            _s2 = _s2.replace("tmp=./conf$$-$RANDOM",
                              "tmp=$TMPDIR/conf$$-$RANDOM")
            if _s2 != _s:
                open(_cfg, "w").write(_s2)
        cfg = (f"CC=/data/service/hnp/bin/clang TMPDIR='{tmpdir}' "
               f"./configure {bld} --disable-nls")
        self.run(cfg, cwd=self.source_folder)
        self.run(f"make -j2 TMPDIR='{tmpdir}'", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        if not os.path.isfile(os.path.join(src, "gpasm", "gpasm")):
            raise ConanException(f"gpasm binary missing under {src}")
        for entry in ("gpasm", "gplink", "gplib", "gpvc", "gpdasm",
                      "include", "lkr", "header"):
            s = os.path.join(src, entry)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(self.package_folder, entry))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "gpasm")
        self.output.info(f"PATH={bindir}")
