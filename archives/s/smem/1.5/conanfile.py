#!/usr/bin/env python3
"""Conan recipe for smem 1.5 — Sufficiently Mem memory reporting tool.

smem is a two-part deliverable:

* ``smem``    — the reporting front end, a single Python 3 script (733 lines)
* ``smemcap`` — the capture helper, a single C file (114 lines) that walks
                /proc and writes a tar archive that ``smem --source`` reads

Only ``smemcap`` is architecture specific, so only it is compiled here; the
``smem`` script is installed verbatim (plus the upstream python3 port in
patches/). Nothing from the upstream deliverable is dropped.

No Makefile is shipped by the 1.5 tag, so build() drives the single
translation unit directly, taking the compiler from Conan conf (R33) instead
of from bare shell environment variables.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SmemConan(ConanFile):
    name = "smem"
    version = "1.5"
    description = "Sufficiently Mem — a tool for meaningful memory reporting (PSS/USS/RSS)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.selenic.com/smem/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("memory", "pss", "smaps", "proc", "cli", "diagnostics")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from Conan conf, never from a bare ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if not cc:
            raise RuntimeError("tools.build:compiler_executables.c is not set in the profile")

        # smemcap.c is a single self-contained translation unit (libc only).
        # Honour the declared build_type instead of hard-coding the level.
        flags = ["-O2"] if self.settings.build_type == "Release" else ["-O0", "-g"]

        # R9: keep it serial; there is nothing to parallelise.
        self.run(f"{cc} {' '.join(flags)} smemcap.c -o smemcap", cwd=self.source_folder)

    def package(self):
        # C capture helper (mode 0755 straight out of the linker)
        copy(self, "smemcap", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Python 3 reporting front end (mode 0755 in the upstream archive)
        copy(self, "smem", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Upstream man page
        copy(self, "smem.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        # Upstream licence text (GPL-2)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Conan normalises modes when copying, so restore the exec bit that
        # both deliverables need (the man page and licence stay 0644).
        for name in ("smem", "smemcap"):
            os.chmod(os.path.join(self.package_folder, "bin", name), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
