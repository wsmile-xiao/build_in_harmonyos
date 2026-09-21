#!/usr/bin/env python3
"""Conan recipe for snapraid 14.9 — OHOS (aarch64) adaptation.

snapraid is a parity-based snapshot backup CLI tool built with GNU
autotools. The release ships a large `make check` regression suite
(74 test blocks run through the memory-checking `checker` binary on
simulated disks under bench/).

Platform adaptations (all applied to the extracted source in build();
no upstream file is modified in the repository):
- E007: config.guess/config.sub learn `HarmonyOS` (uname -s) so configure
  natively canonicalizes the aarch64-unknown-linux-ohos triplet.
- E011/E114: configure's `umask 077` mktemp directory is unwritable on
  HMDFS (setgid 2700 dir -> create denied); relax to umask 022.
- E079: HMDFS cannot create hard links ("Operation not permitted"). A
  transparent `ln` shim tries the real ln first and falls back to
  `cp -p`, so the upstream suite's 4 hard-link commands still execute.
- Upstream already guards single spots with its own --test-skip-fallocate
  test flag; because HMDFS rejects fallocate() for every parity write,
  the same flag is added suite-wide via CHECKFLAGS_COMMON.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# Upstream `make check` base flags (Makefile.am CHECKFLAGS_COMMON) plus
# --test-skip-fallocate for HMDFS, which lacks a working fallocate().
CHECKFLAGS_COMMON = (
    "--test-skip-device --test-skip-self --test-force-progress "
    "--no-warnings --test-parity-limit=3333333 --test-io-advise-none "
    "--test-skip-fallocate"
)

class SnapraidConan(ConanFile):
    name = "snapraid"
    version = "14.9"
    description = "Snapshot backup tool for disk arrays (parity-based data recovery)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.snapraid.it"
    url = "https://github.com/amadvance/snapraid"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _install_ln_shim(self):
        # E079: HMDFS rejects hard links. Transparent shim: real ln first,
        # `cp -p` fallback on "Operation not permitted" (hard links only).
        shim_bin = os.path.join(self.build_folder, "ohos_shim", "bin")
        os.makedirs(shim_bin, exist_ok=True)
        real_ln = shutil.which("ln") or "/bin/ln"
        shim = os.path.join(shim_bin, "ln")
        with open(shim, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "# HMDFS hard-link fallback (E079): try the real ln first;\n"
                "# on Operation-not-permitted fall back to cp -p.\n"
                'REAL_LN="%s"\n' % real_ln
                + 'for a in "$@"; do\n'
                "  case $a in\n"
                "    -s|-sf|-fs|-s-*)\n"
                '      exec "$REAL_LN" "$@"\n'
                "      ;;\n"
                "  esac\n"
                "done\n"
                'if "$REAL_LN" "$@" 2>/dev/null; then\n'
                "  exit 0\n"
                "fi\n"
                'err=$("$REAL_LN" "$@" 2>&1)\n'
                "case $err in\n"
                "  *Operation*not*permitted*)\n"
                '    exec /bin/cp -p "$1" "$2"\n'
                "    ;;\n"
                "  *)\n"
                "    printf '%s\\n' \"$err\" 1>&2\n"
                "    exit 1\n"
                "    ;;\n"
                "esac\n"
            )
        os.chmod(shim, 0o755)
        return shim_bin

    def _tested_shell(self):
        # E386: probe candidate shells from the real build directory and
        # accept one only when `pwd` returns 0 with clean diagnostics;
        # then route configure through it (strips the profile's
        # CONFIG_SHELL, whose hnp bash cannot getcwd() in HMDFS dirs).
        candidates = (
            "/bin/sh",
            "/usr/bin/sh",
            "/usr/bin/bash",
            "/bin/bash",
            "/data/service/hnp/bin/bash",
        )
        for sh in candidates:
            if not os.path.exists(sh):
                continue
            try:
                r = subprocess.run(
                    [sh, "-c", "pwd >/dev/null"],
                    cwd=self.build_folder,
                    capture_output=True,
                    timeout=20,
                )
            except Exception:
                continue
            if r.returncode == 0 and not r.stderr.strip():
                return sh
        raise ConanException("E386: no capability-tested shell for the build directory")

    def build(self):
        apply_conandata_patches(self)

        shell = self._tested_shell()
        prefix = self.package_folder.replace("\\", "/")
        src = self.source_folder.replace("\\", "/")
        jobs = self.conf.get("tools.build:jobs", default=2)
        # basic_layout keeps source/ and build/ apart; snapraid's configure
        # and its make check suite are in-source (bench/ etc.), so every
        # step runs with cwd = source folder.
        self.run(
            "cd '%s' && env -u CONFIG_SHELL SHELL='%s' '%s' ./configure --prefix='%s'"
            % (src, shell, shell, prefix),
            env="conanbuild",
        )
        self.run("cd '%s' && make -j%s" % (src, jobs), env="conanbuild")

        # Upstream regression suite: 74 test blocks via `make check`
        # (check-local), executed here as required. The ln shim + the
        # suite-wide --test-skip-fallocate flag adapt to HMDFS limits.
        shim_bin = self._install_ln_shim()
        self.run(
            "cd '%s' && PATH=\"%s:$PATH\" make check \"CHECKFLAGS_COMMON=%s\""
            % (src, shim_bin, CHECKFLAGS_COMMON),
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder.replace("\\", "/")
        # configure was given --prefix=package_folder, so a plain install
        # populates the package directly (HMDFS-safe, no DESTDIR dance).
        self.run("cd '%s' && make install" % src, env="conanbuild")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
