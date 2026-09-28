#!/usr/bin/env python3
"""Conan recipe for gputils 1.5.2.1 — GNU PIC Utilities (gpasm/gplink/gplib,
gpdasm/gpstrip/gpvo/gpvc; C tools, autotools, SourceForge source, zero deps).

Fix over 1.5.2: the 1.5.x source layout builds gplib/gpdasm/gpstrip/gpvo/gpvc
inside the `gputils/` subdirectory (gpasm/ and gplink/ build only their own
program). The packaging list still named the per-tool directories of the
older layout (gplib/, gpvc/, gpdasm/), which do not exist — and the
`if os.path.isdir(...)` guard skipped them silently, so the published 1.5.2
package shipped without gplib. sdcc's PIC14/PIC16 ports require gpasm *and*
gplink *and* gplib, so those ports could not be enabled against it.

Adaptation lessons applied:
- sdist SHIPS configure (only Makefile.am/Makefile.in lack it) -- so autoreconf is
  SKIPPED deliberately: on CI aclocal is unexecutable (hmdfs forces 0o770 and the
  build uid has no perms; chmod is ineffective there), so we configure directly.
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
    version = "1.5.2.1"
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
        # 1.5.x layout: gpasm/ and gplink/ each build only their own program,
        # while gplib/gpdasm/gpstrip/gpvo/gpvc are all built in gputils/.
        bin_dirs = ("gpasm", "gplink", "gputils")
        data_dirs = ("include", "lkr", "header")
        for entry in bin_dirs + data_dirs:
            s = os.path.join(src, entry)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(self.package_folder, entry))
        # Fail loudly instead of shipping a partial tool set: the isdir guard
        # above is exactly what hid the missing gplib in 1.5.2.
        required = {
            "gpasm": ("gpasm",),
            "gplink": ("gplink",),
            "gputils": ("gpdasm", "gplib", "gpstrip", "gpvo", "gpvc"),
        }
        missing = []
        for d, bins in required.items():
            for b in bins:
                if not os.path.isfile(
                        os.path.join(self.package_folder, d, b)):
                    missing.append(os.path.join(d, b))
        if missing:
            raise ConanException(
                "incomplete gputils tool set, missing: " + ", ".join(missing))

    def package_info(self):
        # The tools live in three directories and all of them must be on
        # PATH: sdcc's device/lib/pic14|pic16 configure resolves gpasm,
        # gplink and gplib independently (AC_PATH_PROG) and aborts if any
        # one of them is missing.
        self.cpp_info.bindirs = [
            d for d in ("gpasm", "gplink", "gputils")
            if os.path.isdir(os.path.join(self.package_folder, d))]
        # gpasm resolves PIC processor headers (p16f877.inc) and gplink its
        # default linker script (16f877_g.lkr) through these variables,
        # falling back to the compiled-in $(datadir)/gputils/<sub> — a path
        # that does not exist inside a Conan package. Declaring them here
        # means every consumer compiles PIC targets without repeating the
        # paths; without them gpasm fails with
        # 'Error[105] Cannot open file. Include file "p16f877.inc" not found'.
        for var, sub in (("GPUTILS_HEADER_PATH", "header"),
                         ("GPUTILS_LKR_PATH", "lkr")):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                self.runenv_info.define_path(var, d)
                self.buildenv_info.define_path(var, d)
        self.output.info(
            f"PATH={os.pathsep.join(self.cpp_info.bindirs)}")
