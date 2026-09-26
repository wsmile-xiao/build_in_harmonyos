#!/usr/bin/env python3
"""Conan recipe for mairix 0.24 — index and search email folders.

mairix (Richard Curnow, sourceforge) builds a hash database over
maildir/mbox/mh folders and answers searches by symlinking matches into
an output folder.  Pure C, hand-written configure (sed-generates
Makefile from Makefile.in), no autoconf machinery.

Platform notes:
- zlib/bzlib mbox support is left disabled (default): the published
  test-suite exercises plain folders only, and keeping the tool
  dependency-free makes the delivery self-contained.  Documented
  degradation: gzipped/bzip2ed mboxes are not indexed.
- LD_LIBRARY_PATH is explicitly emptied during build (lld/libxml2
  shield — CI-021 build #48068, mechanism in libodfgen/libabw).
- The dfasyn subdirectory is compiled as a build-time generator and run
  on the same machine (build = host), so no cross toolchain is needed.
- Nothing is stripped on install (llvm-strip output is refused by the
  platform's exec policy — yices 2.7.0 evidence + knowledge draft).
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class MairixConan(ConanFile):
    name = "mairix"
    version = "0.24"
    description = ("mairix - index and search email in maildir, mbox or "
                   "mh folders")
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/mairix/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # upstream configure generates Makefile in the current directory
        # (rm -f Makefile) — run it inside a copy of the source tree so
        # the conan source folder stays pristine.
        build = self.build_folder
        self._copy_tree(self.source_folder, build)
        env = dict(os.environ)
        # lld/libxml2 shield — see class docstring.
        env["LD_LIBRARY_PATH"] = ""
        env["CC"] = self._cc()
        env["CFLAGS"] = "-O2 -Wall"
        shell = self._resolve_shell()
        env["SHELL"] = shell
        env["CONFIG_SHELL"] = shell
        tmpdir = os.path.join(build, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir
        # umask 022 (hmdfs permission-bit trap, buildtorrent precedent —
        # a 077-created config.log/docheck tree ends up unwritable)
        cmd = (f"umask 022; {shlex.quote(shell)} ./configure "
               "--prefix=/ < /dev/null")
        completed = subprocess.run(cmd, shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(build, env)
            raise ConanException(
                f"configure failed (rc={completed.returncode})")
        completed = subprocess.run("make -j2 < /dev/null",
                                   shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(build, env)
            raise ConanException("make failed")

    def package(self):
        build = self.build_folder
        copy(self, "mairix", src=build,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # ── helpers ─────────────────────────────────────────────────────────

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if compilers:
            if isinstance(compilers, str):
                import json
                try:
                    compilers = json.loads(compilers)
                except ValueError:
                    compilers = {}
            if compilers.get("c"):
                return compilers["c"]
        return "clang"

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _copy_tree(self, src, dst):
        shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)

    def _dump_failure_diagnostics(self, directory, environment):
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CFLAGS", "CPPFLAGS", "LDFLAGS",
                     "LD_LIBRARY_PATH", "SHELL"):
            if name in environment:
                self.output.info(f"{name}={environment[name]}")
        config_log = os.path.join(directory, "config.log")
        if os.path.isfile(config_log):
            with open(config_log, errors="replace") as handle:
                lines = handle.readlines()
            for line in lines[-25:]:
                self.output.info(line.rstrip())
