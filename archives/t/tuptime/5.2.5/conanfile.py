#!/usr/bin/env python3
"""Conan recipe — tuptime 5.2.5.

tuptime reports historical and statistical system uptime, preserved across
reboots.  It is a **single-file Python 3 command line program**
(``src/tuptime``, shebang ``#!/usr/bin/env python3``) backed by a SQLite
database.  The upstream release tree contains no C/C++ source and no build
system at all, so this recipe follows the SKILL "header-only / 无构建打包族"
template, variant C (interpreted script tool — install, do not compile):
there is no ``build()`` and no fake compile log (R34).

Language note (R47): ``lang-preflight`` against the upstream tree reports
``detected_language = python`` (100 % of the sources), while the dispatched
task language defaults to ``cpp``.  This package was adapted under explicit
user authorisation as a script-tool package (the skill's variant C above
exists for exactly this class of software); no C/C++ compilation is involved.

Upstream: https://github.com/rfmoz/tuptime — release 5.2.5, GPL-2.0-or-later.
Runtime requirement: a Python 3 interpreter (standard library only — sqlite3,
argparse, locale, platform, signal, logging, time, datetime).  There are no
third-party ``requires``.

HarmonyOS (OHOS) port — patches/0001-src-tuptime.patch
------------------------------------------------------
CPython on OpenHarmony reports ``sys.platform == 'ohos'``.  Upstream selects a
backend with ``sys.platform.startswith('linux')`` / BSD tuple, and any other
value aborts with ``System = ohos not supported`` (exit 1) *before* a single
record is written — the tool is unusable on OHOS without the patch.  OHOS runs
the HongMeng kernel but still exposes the Linux ``/proc`` interface
(``/proc/uptime``, ``/proc/stat``, ``/proc/sys/kernel/random/boot_id``) and the
``clock_gettime()`` clocks consumed by ``os_linux()``, so ``ohos`` is routed to
the Linux backend.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TuptimeConan(ConanFile):
    name = "tuptime"
    version = "5.2.5"
    description = ("Report historical and statistical system uptime, preserved "
                   "across reboots (uptime with a SQLite register back end)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rfmoz/tuptime"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # No compilation happens for an interpreted script, but the four settings
    # are declared so the package participates in the cross-build matrix the
    # same way every other recipe does (R32/PF8).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: the OHOS recipe accepts both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tuptime is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Interpreted script tool (SKILL "无构建打包族", variant C): there is
        # nothing to compile, so the single build step is applying the OHOS
        # portability patch to the fetched script.  No compilation is invented
        # and no compile log is fabricated (R34).
        apply_conandata_patches(self)

    # No build(): the upstream artifact *is* the script (R34 — installed as-is,
    # no fabricated compilation step).

    def package(self):
        copy(self, "tuptime",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # The release tarball stores src/tuptime as mode 0664; the official
        # installer ships it with `install -m 755` (tuptime-install.sh:121).
        # It is a shebang script, so the executable bit is part of the
        # artifact, not cosmetic.
        os.chmod(os.path.join(self.package_folder, "bin", "tuptime"), 0o755)
        copy(self, "tuptime.1",
             src=os.path.join(self.source_folder, "src", "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "tuptime-manual.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "tuptime"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        # Nothing is compiled and the shipped script is architecture neutral,
        # so the package id carries no settings (header-only template, var C).
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
