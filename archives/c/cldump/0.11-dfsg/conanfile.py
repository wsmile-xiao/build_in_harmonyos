#!/usr/bin/env python3
"""Conan recipe — cldump 0.11-dfsg (Clarion database extractor CLI tool).

Build system: plain hand-written Makefile in src/ (no configure, no install,
no check/test targets). Single binary `cldump`, no libraries, no Conan
dependencies (libc only: stdio/stdlib/string + mmap + iconv resolved by the
system libc, same as Debian which builds with plain dh_auto_build).

OHOS adaptations:
  - patches/0001 changes `CFLAGS =` to `CFLAGS +=` and links with
    `$(LDFLAGS)` (Debian 01-hardening.patch same approach), so flags
    injected by the Conan buildenv are honoured instead of overwritten.
  - The compiler comes from `tools.build:compiler_executables` and is passed
    as `make CC=...` on the command line (R33: never bare $CC in self.run).
  - Upstream ships no test suite (see test_package/MANIFEST.yml audit), so
    build() does not call a `check` target; it smoke-validates the freshly
    built binary (`--version` must exit 0) when the target can run here.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CldumpConan(ConanFile):
    name = "cldump"
    version = "0.11-dfsg"
    description = "Clarion database files extractor (dumps Clarion .dat to text/SQL/CSV)"
    license = "GPL-2.0-only"
    homepage = "https://salsa.debian.org/debian/cldump"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os={} not supported".format(self.settings.os)
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _resolve_cc(self):
        """Profile hardcodes /data/service/hnp/bin/clang which may not exist
        on the device (xz 5.8.3.2 precedent); prefer the configured path only
        when it is an executable file, else fall back to PATH lookup."""
        compilers = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        configured = compilers.get("c")
        if (
            configured
            and os.path.isfile(configured)
            and os.access(configured, os.X_OK)
        ):
            return configured
        found = shutil.which("clang")
        if found:
            if configured:
                self.output.info(
                    "Configured CC '{}' not usable, using '{}' from PATH".format(
                        configured, found
                    )
                )
            return found
        if configured and shutil.which(configured):
            return configured
        return configured or "clang"

    def build(self):
        # HMDFS: configure/make temp dirs created with restrictive umask fail;
        # plain make needs no temp dirs, but keep the worker-wide guard.
        try:
            os.umask(0)
        except OSError:
            pass
        apply_conandata_patches(self)

        cc = self._resolve_cc()

        src_dir = os.path.join(self.source_folder, "src")
        # R9: single job; command-line CC overrides the Makefile default.
        self.run('make -j1 CC="{}"'.format(cc), cwd=src_dir, env="conanbuild")

        if can_run(self):
            self._behavior_check(src_dir)
        else:
            self.output.info(
                "Skipping tool behavior check: target binary cannot run here"
            )

    def _behavior_check(self, src_dir):
        """R51: upstream ships no automated suite; validate the real binary
        reaches its CLI entry points (version/help) instead."""
        exe = os.path.join(src_dir, "cldump")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration(
                "cldump binary was not produced in {}".format(src_dir)
            )
        self.run('"{}" --version'.format(exe), env="conanbuild")
        self.output.info("  [ok] freshly built cldump --version exits 0")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(
            self,
            "cldump",
            src=os.path.join(self.source_folder, "src"),
            dst=bindir,
        )
        # Man page ships in-tree; keep it next to the binary install.
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(mandir, exist_ok=True)
        copy(
            self,
            "cldump.1",
            src=os.path.join(self.source_folder, "src"),
            dst=mandir,
        )

    def package_info(self):
        # CLI tool: no linkable libraries or headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
