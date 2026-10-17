#!/usr/bin/env python3
"""Conan recipe — clock-setup 0.168 (raw Makefile, single C tool).

clock-setup is the Debian installer clock-setup udeb. Its only compiled
artifact is set-date-epoch, a tiny C program that resets the system clock
to the epoch when it reads a pre-1970 date. The remaining upstream files
are debian-installer shell scripts (debconf postinst + finish-install
hook) with no test suite; upstream test audit lives in
test_package/MANIFEST.yml (upstream_tests_exist: false).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class ClockSetupConan(ConanFile):
    name = "clock-setup"
    version = "0.168"
    description = "Debian installer clock setup helper: set-date-epoch resets a pre-1970 system date to the epoch"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/installer-team/clock-setup"
    url = "https://salsa.debian.org/installer-team/clock-setup"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)
        # Upstream builds in-source (Makefile compiles set-date-epoch.c
        # next to the sources, no VPATH support).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_cc(self):
        # Preflight 2026-09-09 round 2: profile's
        # tools.build:compiler_executables:c pointed at
        # /data/service/hnp/bin/clang which does not exist on the device
        # (make: No such file or directory, Error 127). So a conf value is
        # only used when it actually exists/executes; otherwise fall back
        # to PATH lookup (hmbs prepends real tool dirs to PATH).
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        candidates = [
            compiler_executables.get("c"),
            os.environ.get("CC"),
            shutil.which("clang"),
            shutil.which("cc"),
            shutil.which("gcc"),
        ]
        for cand in candidates:
            if not cand:
                continue
            # Bare tool names (no slash) rely on PATH at run time.
            if os.path.basename(cand) == cand:
                return cand
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        # Last resort: historic HNP path, else bare clang (clear error).
        for cand in ("/data/service/hnp/bin/clang", "clang", "cc"):
            if os.path.basename(cand) == cand:
                if shutil.which(cand):
                    return cand
            elif os.path.isfile(cand):
                return cand
        return "clang"

    def build(self):
        # R33: compiler comes from Conan conf dict, never from shell env vars
        # as primary source; PATH fallback only when the conf path is
        # missing on the device (round-2 evidence above).
        cc = self._resolve_cc()
        self.output.info("clock-setup resolved CC=%s" % cc)
        # Upstream Makefile honors a command-line CC override
        # (CC := gcc inside the file). R9: keep -j1.
        make_bin = os.environ.get("HMBS_MAKE") or "make"
        self.run("{make_bin} CC={cc} -j1 build".format(
            make_bin=make_bin, cc=cc), cwd=self.source_folder)

    def package(self):
        copy(self, "set-date-epoch", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        try:
            os.chmod(os.path.join(self.package_folder, "bin", "set-date-epoch"), 0o755)
        except OSError:
            pass

    def package_info(self):
        # Command-line tool package, no library to link.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
