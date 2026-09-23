#!/usr/bin/env python3
"""Conan recipe - myman 0.7.1 (custom configure + GNU make, ncursesw).

myman (MyMan) is a text-terminal Pac-Man-style video game by Benjamin C.
Wiley Sittler, written in C and built with a custom hand-written
configure script plus a GNU-make based Makefile.

Build notes for HarmonyOS PC (aarch64):
  * Display driver: ncurses wide-char (ncursesw), selected via
    `./configure --with-ncursesw`; the Makefile calls `${NCURSESW_CONFIG}
    --cflags/--libs` so we point NCURSESW_CONFIG at the conan ncurses
    package's relocated `ncursesw6-config`.
  * The upstream Makefile runs a `coreutils.ok`/`sed.ok` sanity check
    that probes GNU `install --strip`, `rmdir --ignore-fail-on-non-empty`
    and `sed --silent`.  HarmonyOS only ships toybox, so tiny wrapper
    scripts (conf/install, conf/rmdir, conf/sed) are generated that
    answer the help probes and delegate the real work to toybox.
  * Configure runs from a non-HMDFS work directory under
    /data/storage/el2/base (E011: HMDFS strips execute bits / breaks
    temp-dir permission semantics used by autotools-style generators).
  * The produced `myman` executable embeds all game variants and sizes
    as built-in data (BUILTIN_MAZE/TILE/SPRITE) and links ncursesw
    statically; it only depends on libc at runtime.
"""
import hashlib
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MymanConan(ConanFile):
    name = "myman"
    version = "0.7.1"
    description = "MyMan - a text-terminal Pac-Man-style video game (ncurses)"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/myman/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _ohos_work_root = "/data/storage/el2/base"
    _ohos_bash = "/data/service/hnp/bin/bash"

    def requirements(self):
        # ncurses/6.6 (wide-char static build) is published on ohpcd.
        self.requires("ncurses/6.6")

    def export_sources(self):
        # conandata.yml declares an empty patch set; this hook keeps the
        # recipe template-complete (G1) and exports any future patches.
        export_conandata_patches(self)

    def source(self):
        sources = self.conan_data["sources"]
        # SourceForge "/download" URL has no archive extension, so conan's
        # get() cannot auto-detect the archive type. Hint the filename.
        get(
            self,
            sources["url"],
            sha256=sources["sha256"],
            filename="myman-wip-2009-10-30.tar.gz",
            strip_root=True,
        )

    # -- helpers -----------------------------------------------------

    def _work_dir(self):
        """Deterministic per-build working dir under non-HMDFS storage."""
        key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        return os.path.join(
            self._ohos_work_root,
            ".conan-build-myman-{0}-{1}".format(self.version, key),
        )

    def _reset_dir(self, path):
        if os.path.lexists(path):
            if os.path.islink(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)

    def _write_wrappers(self, work):
        """Create GNU-flavored tool wrappers (toybox backend)."""
        conf_dir = os.path.join(work, "conf")
        os.makedirs(conf_dir, exist_ok=True)
        wrappers = {
            "install": [
                "#!/bin/sh",
                'for a in "$@"; do',
                '  if [ "$a" = "--help" ] || [ "$a" = "-h" ]; then',
                "    printf '%s\\n' 'Usage: install [OPTION]... [-T] SOURCE... DEST'",
                "    printf '%s\\n' '  -s, --strip                strip symbol tables'",
                "    printf '%s\\n' '  -d, --directory            treat all arguments as directory names'",
                "    printf '%s\\n' '  -m, --mode=MODE            set permission mode'",
                "    exit 0",
                "  fi",
                "done",
                'exec /bin/toybox install "$@"',
            ],
            "rmdir": [
                "#!/bin/sh",
                'for a in "$@"; do',
                '  if [ "$a" = "--help" ] || [ "$a" = "-h" ]; then',
                "    printf '%s\\n' 'Usage: rmdir [OPTION]... DIRECTORY...'",
                "    printf '%s\\n' '  --ignore-fail-on-non-empty  ignore failures caused by non-empty directories'",
                "    exit 0",
                "  fi",
                "done",
                'exec /bin/toybox rmdir "$@"',
            ],
            "sed": [
                "#!/bin/sh",
                'for a in "$@"; do',
                '  if [ "$a" = "--help" ] || [ "$a" = "-h" ]; then',
                "    printf '%s\\n' 'Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...'",
                "    printf '%s\\n' '  -n, --silent, --quiet     suppress automatic printing of pattern space'",
                "    exit 0",
                "  fi",
                "done",
                'exec /bin/toybox sed "$@"',
            ],
        }
        for name, lines in wrappers.items():
            path = os.path.join(conf_dir, name)
            with open(path, "w", encoding="utf-8", newline="\n") as stream:
                stream.write("\n".join(lines) + "\n")
            os.chmod(path, 0o755)

    def _myman_env(self):
        """Drop environment variables that would override make defaults."""
        return [
            "env",
            "-u",
            "LD",
            "-u",
            "CPPFLAGS",
            "-u",
            "LDFLAGS",
            "-u",
            "CFLAGS",
        ]

    def build(self):
        # Empty patch set today (no upstream source edits needed); keep the
        # standard hook so future conandata patches apply automatically.
        apply_conandata_patches(self)

        ncurses = self.dependencies["ncurses"]
        nc_pkg = ncurses.package_folder
        nclib = os.path.join(nc_pkg, "lib")
        ncursesw_config = os.path.join(nc_pkg, "bin", "ncursesw6-config")
        bash = self._ohos_bash

        work = self._work_dir()
        self._reset_dir(work)
        # Copy source out of HMDFS conan cache before configure/make (E011).
        shutil.copytree(self.source_folder, work, symlinks=True)
        self._write_wrappers(work)

        def run(cmd):
            self.run(" ".join(cmd), cwd=work)

        # 1) configure (host == build: native OHOS toolchain)
        run(
            self._myman_env()
            + [bash, "configure", "--with-ncursesw",
               "CC=clang", "CFLAGS=-O2",
               "LDFLAGS=-L{0}".format(nclib),
               "SHELL={0}".format(bash)]
        )

        # 2) make (single job; upstream Makefile is not parallel-safe)
        make_prefix = (
            self._myman_env()
            + ["make", "-j1",
               "NCURSESW_CONFIG={0}".format(ncursesw_config),
               "CC=clang", "CFLAGS=-O2",
               "LDFLAGS=-L{0}".format(nclib),
               "INSTALL={0}/conf/install".format(work),
               "RMDIR={0}/conf/rmdir".format(work),
               "SED={0}/conf/sed".format(work)]
        )
        run(make_prefix)

        # 3) make install into a private staging dir (DESTDIR).
        #    NB: the "install" target MUST be passed explicitly - the default
        #    goal is `all`, so a bare `make ... DESTDIR=...` only rebuilds the
        #    game and leaves the stage tree empty (W3 package() -> empty pkg).
        stage = os.path.join(work, "stage")
        os.makedirs(stage, exist_ok=True)
        run(make_prefix + ["install", "DESTDIR={0}".format(stage)])

    def package(self):
        stage_root = os.path.join(
            self._work_dir(), "stage", "usr", "local"
        )
        # Executable + man page + docs (LICENSE etc.)
        copy(self, "myman",
             src=os.path.join(stage_root, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "myman.6",
             src=os.path.join(stage_root, "share", "man", "man6"),
             dst=os.path.join(self.package_folder, "share", "man", "man6"))
        copy(self, "*",
             src=os.path.join(stage_root, "share", "doc", "myman-0.7.1"),
             dst=os.path.join(self.package_folder, "share", "doc", "myman"))

        # OHOS kernel refuses to exec an ELF without a valid .codesign
        # signature (E077). Sign the packaged binary (and restore +x).
        if str(self.settings.os) == "OHOS":
            self._sign_elf_if_ohos(
                os.path.join(self.package_folder, "bin", "myman"))

    # -- OHOS ELF signing (E077; same convention as boxes/abbtr) ---------

    @staticmethod
    def _has_ohos_signature(path):
        """True if the ELF already carries a .codesign/.note.ohos section."""
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        """Four-step OHOS post-install sign flow (order is not negotiable):

        copy to tmp -> llvm-objcopy --remove-section .codesign (best-effort)
        -> binary-sign-tool sign -selfSign 1 -> move back -> chmod 755.
        """
        if not os.path.isfile(path):
            return
        # Already signed: only restore the exec bit (E077: sign tool cannot
        # overwrite an existing signature section).
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return

        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(
                "OHOS packaging requires binary-sign-tool and llvm-objcopy")

        tmp_in = "{0}.unsigned".format(path)
        tmp_out = "{0}.signed".format(path)
        shutil.copy2(path, tmp_in)
        # Remove any stale signature before (re)signing; failure is fine when
        # no .codesign section is present yet.
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", tmp_in],
            capture_output=True,
            timeout=30,
        )
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        if os.path.isfile(tmp_in):
            os.unlink(tmp_in)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.conf_info.define(
            "user.myman:exe",
            os.path.join(self.package_folder, "bin", "myman"),
        )
