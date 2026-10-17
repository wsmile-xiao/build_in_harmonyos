#!/usr/bin/env python3
"""Conan recipe for lbdb 0.57 (Little Brother's DataBase, Roland Rosenfeld).

Package shape (verified first-hand against lbdb-0.57.tar.gz, 109 files):
  * autotools (configure / configure.ac / generated Makefile).  It compiles 5
    C helpers -- fetchaddr, qpto8bit, lbdb_dotlock (from dotlock.c + helpers.c,
    plus rfc2047.c / rfc822.c objects) -- and expands ~45 ``*.in`` templates into
    the real command surface: the ``lbdbq`` front-end, ``lbdb-fetchaddr``,
    ``lbdb-munge``/``munge``, ``lbdb_lib``, the ``m_*.sh`` query modules, two
    awk helpers and four perl helpers (nodelist2lbdb, palm_lsaddr,
    mutt_ldap_query, vcquery).
  * NO external Conan dependency.  The only header pulled from outside libc is
    ``<iconv.h>`` (rfc2047.c); the OHOS libc provides it, so ``@LIBICONV@``
    stays empty.  No zlib / openssl / glib anywhere in the tree.

HarmonyOS PC interpreter reality -- measured on the build host (see notes.md):
  /bin/sh          = toybox ash, PROVEN to run every construct these scripts use
                     (``[[ ]]``, arrays, ``${v//x/y}``, ``==``, ``local``, named
                     functions) -> the safe, non-machine-bound shebang.
  /bin/awk         = toybox awk, present -> portable awk target.
  /usr/bin/perl    = ABSENT; perl lives at /data/service/hnp/bin/perl (on PATH),
                     so ``#!/usr/bin/env perl`` is the portable form (E049).
  /usr/bin/bash,
  /bin/bash        = ABSENT; bash exists only per-user (harmonybrew) or as the
                     HNP bash whose getcwd() is denied off "/" (breaks the
                     autoconf driver -- hence CONFIG_SHELL is pinned to /bin/sh).

configure fills ``#! @SH@`` / ``#! @PERL@`` / ``#! @AWK@`` in every ``*.in``
template with the *build-host* absolute interpreter (AC_PATH_PROG).  To keep the
installed command surface portable across OpenHarmony machines we (a) pin SH=/bin/sh
and AWK=/bin/awk at configure time and (b) re-normalise the installed shebangs of
every delivered bin/libexec script to a platform-resolvable interpreter (E049
shebang-portable-fix, same family as archives/j/jigit/1.22 mkjigsnap fix).
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LbdbConan(ConanFile):
    name = "lbdb"
    version = "0.57"
    description = ("Little Brother's DataBase: a lightweight mail alias/address "
                   "lookup database with query tools for MUA integration")
    license = "GPL-2.0-or-later"
    homepage = "https://www.spinnaker.de/lbdb/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is supported on Linux and OHOS only, not {self.settings.os}")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        # In-tree build: lbdb's generated Makefile expands *.in -> scripts in the
        # build tree and installs the C helpers with hand-written $(CC) rules; a
        # plain basic_layout with the commands issued in self.source_folder is the
        # shape that matches this Makefile (same reason as archives/j/jigit/1.22).
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prefix(self):
        return self.package_folder.replace("\\", "/")

    def _configure_args(self):
        prefix = self._prefix()
        # NOTE: we intentionally do NOT let Conan add --build/--host/--target:
        # they make autoconf treat the build as cross-compiling and skip every
        # AC_RUN_IFELSE/AC_PATH_PROG probe (E007/E160).  config.guess guesses the
        # OHOS triplet natively once patches/0001 is applied.
        return [
            f"--prefix={prefix}",
            f"--bindir={prefix}/bin",
            f"--libexecdir={prefix}/libexec",
            f"--sysconfdir={prefix}/etc",
            f"--mandir={prefix}/share/man",
            f"--datarootdir={prefix}/share",
            # Pin portable interpreters so generated shebangs are not bound to
            # this build host (E049).  configure skips the bash probe when SH is
            # preset; the .awk shebangs are still normalised in package().
            "SH=/bin/sh",
            "AWK=/bin/awk",
        ]

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Replace Conan's default install-dir args with our explicit prefix set;
        # AutotoolsToolchain.generate() still exports CC/CFLAGS/LDFLAGS through
        # the conanbuild env, which our hand-run ./configure below inherits (R33).
        tc.configure_args = self._configure_args()
        tc.generate()
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _addexec(path):
        os.chmod(path, os.stat(path).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _relax_hmdfs_scratch_dir(self, configure_path):
        """E129: swap autoconf's mktemp-based config.status scratch dir for plain mkdir.

        autoconf 2.72 creates config.status' private temp dir with
        `(umask 077 && mktemp -d "./confXXXXXX")`.  On this device toybox
        `mktemp -d` returns a directory the kernel then refuses O_WRONLY opens
        inside, so `config.status` dies at
        "can't create ./confXXXXXX/subs1.awk: Permission denied" /
        "config.status: error: could not setup config files machinery".
        Plain mkdir yields a writable drwxrws--x instead (measured; same fix as
        archives/j/jigit/1.22).  The string is inside the here-doc configure
        streams into ./config.status, so editing configure fixes the generated
        config.status.  Exactly one occurrence in this configure.
        """
        replace_in_file(
            self, configure_path,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"',
            'tmp=./conf$$-$RANDOM\n'
            '  mkdir "$tmp"', strict=True)

    def build(self):
        apply_conandata_patches(self)   # 0001: config.guess/config.sub -> ohos (E007)
        src = self.source_folder

        # E129: relax the HMDFS-undrinkable mktemp scratch dir before configure
        # generates (and runs) config.status.
        self._relax_hmdfs_scratch_dir(os.path.join(src, "configure"))

        # HMDFS hands out 0660 files: every generated build script must be made
        # executable again before autotools/sh can run it.
        for rel in ("configure", "config.guess", "config.sub", "install-sh",
                    "mkinstalldirs", "missing", "compile", "ltmain.sh"):
            path = os.path.join(src, rel)
            if os.path.isfile(path):
                self._addexec(path)

        args = " ".join(self._configure_args())
        # CONFIG_SHELL=/bin/sh: the OHOS profile exports CONFIG_SHELL to the HNP
        # bash, which is denied getcwd() everywhere except "/" and re-execs
        # configure, killing it with "working directory cannot be determined"
        # (measured; same finding recorded for archives/j/jigit/1.22).  Drive
        # configure with toybox /bin/sh instead.
        self.run(f"CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ./configure {args}",
                 cwd=src, env="conanbuild")
        self.run("make -j1", cwd=src, env="conanbuild")

    @staticmethod
    def _normalized_shebang(first_line):
        """Map a machine-bound interpreter shebang to a portable OHOS one.

        Returns the new '#!' line, or None when the line must be left alone.
        """
        line = first_line[2:].strip()
        if not line:
            return None
        parts = line.split()
        base = os.path.basename(parts[0])
        tail = parts[1:]
        if base in ("sh", "ash", "dash"):
            return "#! /bin/sh" + ((" " + " ".join(tail)) if tail else "")
        if base in ("bash", "ksh"):
            # toybox /bin/sh is proven to run every construct lbdb's scripts use.
            return "#! /bin/sh"
        if base == "perl":
            # /usr/bin/perl is absent; the HNP perl is on PATH -> env form (E049).
            return "#! /usr/bin/env perl"
        if base in ("awk", "gawk", "mawk", "nawk"):
            return "#! /bin/awk" + ((" " + " ".join(tail)) if tail else "")
        return None

    def _fix_installed_shebang(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        if not data.startswith(b"#!"):
            return                      # ELF binary (fetchaddr/qpto8bit/lbdb_dotlock)
        nl = data.find(b"\n")
        first = data[:nl] if nl != -1 else data
        try:
            new_line = self._normalized_shebang(first.decode("utf-8"))
        except UnicodeDecodeError:
            return
        if new_line is None:
            return
        rest = data[nl:] if nl != -1 else b"\n"
        with open(path, "wb") as handle:
            handle.write(new_line.encode("utf-8") + rest)

    def package(self):
        # lbdb installs via the absolute --prefix (not DESTDIR), so run make
        # install here where package_folder exists.
        self.run("make install", cwd=self.source_folder, env="conanbuild")

        for sub in ("bin", "libexec"):
            directory = os.path.join(self.package_folder, sub)
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                if not os.path.isfile(path):
                    continue
                self._addexec(path)
                self._fix_installed_shebang(path)   # E049 portable shebang

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
