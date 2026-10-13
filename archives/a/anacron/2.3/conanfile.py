#!/usr/bin/env python3
"""Conan recipe for anacron 2.3 — periodic command scheduler (upstream plain Makefile).

Upstream facts (measured on the 23 B / 24085-byte Debian orig tarball):
  * 18 entries, single build file = hand-written ``Makefile`` (no configure,
    no CMake, no autotools despite the stray ``configure.ac`` name).
  * two absolute paths are burned into the binary at compile time through
    ``-DSPOOLDIR`` / ``-DANACRONTAB``; ``main()`` does ``chdir(SPOOLDIR)``
    unconditionally and the only runtime override upstream offers is
    ``-t`` for the anacrontab — the spool dir has none.
  * ``runjob.c`` creates its per-job temp file through
    ``tempnam(NULL, NULL)`` → ``P_tmpdir`` = ``/tmp``, which is read-only on
    OHOS/HarmonyOS (and this libc ignores ``$TMPDIR``).
  * ``readtab.c`` needs GNU obstack, which musl/HarmonyOS does not ship.
    The registry DOES ship one (``musl-obstack/1.2.3``, required by
    dwarves/dwz/box64/elfutils) — an earlier draft only probed the four
    exact names ``obstack``/``gnulib``/``libiberty``/``gnu-obstack`` and
    missed it. We still vendor here on purpose: this is an application
    package, so vendoring avoids a shared dependency and its SONAME
    packaging surface. Vendored files are the GNU C Library
    ``obstack.h``/``obstack.c`` (LGPL-2.1-or-later; LGPL-2.1 §6 permits
    re-licensing to GPL v2+) under ``third_party/obstack/``.

See notes.md for the full adaptation record.
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


class AnacronConan(ConanFile):
    name = "anacron"
    version = "2.3"
    description = "Periodic command scheduler that runs missed jobs after boot"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/sid/anacron"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Vendored GNU obstack (musl/HarmonyOS ships no <obstack.h>).
    exports_sources = "third_party/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"anacron requires a POSIX host, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # ``exports_sources`` already lands third_party/ inside the source
        # folder; flatten it so the upstream Makefile's ``wildcard *.c``
        # picks obstack.c up together with the rest of the objects.
        # (``self.recipe_folder`` points at the export folder, not at the
        # export_sources folder, hence the source_folder-based path.)
        vendor = os.path.join(self.source_folder, "third_party", "obstack")
        if not os.path.isdir(vendor):
            raise ConanInvalidConfiguration(
                "vendored obstack not found — exports_sources did not ship third_party/"
            )
        for fname in ("obstack.h", "obstack.c"):
            copy(self, fname, src=vendor, dst=self.source_folder)

    def _make_vars(self):
        """Make variables shared by build() and package().

        PREFIX must stay empty and every install dir must be passed
        explicitly: upstream's ``installdirs`` target concatenates
        ``$(PREFIX)$(SPOOLDIR)``, which only works while SPOOLDIR is
        relative, while the compiled-in SPOOLDIR/ANACRONTAB macros must be
        absolute. Passing all four absolute paths sidesteps the double
        concatenation and keeps the macros and the installed layout in sync.
        """
        pf = self.package_folder.replace("\\", "/")
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp_execs.get("c") or "clang"
        if not os.path.exists(cc):
            cc = "clang"
        return {
            "CC": f'"{cc}"',
            # readtab.c pulls the vendored header in as <obstack.h>, i.e. through
            # the system include path, so the source dir has to be searched.
            "CPPFLAGS": '"-I."',
            "PREFIX": "",
            "BINDIR": f'"{os.path.join(pf, "bin")}"',
            "MANDIR": f'"{os.path.join(pf, "share", "man")}"',
            "SPOOLDIR": f'"{os.path.join(pf, "var", "spool", "anacron")}"',
            "ANACRONTAB": f'"{os.path.join(pf, "etc", "anacrontab")}"',
            # HarmonyOS has no `install(1)` (coreutils ships it as `ginstall`);
            # these three are POSIX-portable stand-ins.
            "INSTALL_DIR": '"mkdir -p"',
            "INSTALL_PROGRAM": "cp",
            "INSTALL_DATA": "cp",
        }

    @staticmethod
    def _mkstr(vars_):
        return " ".join(f"{k}={v}" for k, v in vars_.items())

    # Delivery convention: source-level fixes live in build(), NOT in patches/.
    # `finish` step 1 runs `refresh-patch --auto`, which regenerates patches/
    # from the exploration tree's edit tracker and moves hand-written patches
    # into patches/.patch-backup-<ts> — that stray hidden dir trips the CI
    # junk gate and desyncs conandata.yml. §12.50 (5) records this exact
    # two-round failure (gnuspool #10775) and settles on this convention.
    _SOURCE_FIXES = (
        (
            "gregor.c",
            "    const int isleap; /* save three calls to leap() */",
            "    int isleap; /* save three calls to leap() */",
            # upstream declares a const automatic and then assigns to it;
            # clang rejects it outright ("cannot assign to variable ...").
            "const automatic assigned after declaration, rejected by clang",
        ),
        (
            "main.c",
            '#include <string.h>\n#include "global.h"',
            '#include <string.h>\n#include <stdlib.h>\n#include "global.h"',
            "getenv() needs stdlib.h"
        ),
        (
            "main.c",
            '    if (chdir(SPOOLDIR)) die_e("Can\'t chdir to " SPOOLDIR);',
            "    /* Upstream offers -t for the anacrontab but no runtime override\n"
            "     * for the spool dir, and the compiled-in path is not writable on\n"
            "     * OHOS/HarmonyOS. Keep SPOOLDIR as the default, allow redirect. */\n"
            "    spool_dir = getenv(\"ANACRON_SPOOL\");\n"
            "    if (spool_dir == NULL || spool_dir[0] == '\\0') spool_dir = SPOOLDIR;\n"
            "    if (chdir(spool_dir)) die_e(\"Can\'t chdir to %s\", spool_dir);",
            "chdir() has no runtime escape hatch upstream"
        ),
        (
            "main.c",
            "char *program_name;\nchar *anacrontab;",
            "char *program_name;\nchar *anacrontab;\nchar *spool_dir;",
            "declaration for the ANACRON_SPOOL override",
        ),
        (
            "runjob.c",
            "\tname = tempnam(NULL, NULL);",
            "\t/* tempnam(NULL,NULL) resolves to P_tmpdir=/tmp, read-only here, and\n"
            "\t * this libc ignores $TMPDIR. main() already chdir()ed into the spool\n"
            "\t * dir we own, so use it. */\n"
            "\tname = tempnam(\".\", \"an\");",
            "P_tmpdir is hardwired to the read-only /tmp"
        ),
        (
            "runjob.c",
            "    struct passwd *ps;\n\n"
            "    ps = getpwuid(geteuid());\n"
            "    if (ps == NULL) die_e(\"getpwuid() error\");\n"
            "    return ps->pw_name;",
            "    struct passwd *ps;\n"
            "    const char *env_name;\n\n"
            "    ps = getpwuid(geteuid());\n"
            "    if (ps != NULL) return ps->pw_name;\n"
            "    /* app/sandbox uids are deliberately absent from /etc/passwd on\n"
            "     * OHOS/HarmonyOS, so getpwuid() returns NULL. This address only\n"
            "     * fills an informational mail header; do not abort the run. */\n"
            "    env_name = getenv(\"LOGNAME\");\n"
            "    if (env_name == NULL || env_name[0] == '\\0') env_name = getenv(\"USER\");\n"
            "    if (env_name == NULL || env_name[0] == '\\0') env_name = \"anacron\";\n"
            "    return (char *) env_name;",
            "getpwuid NULL would otherwise die_e() the whole run"
        ),
    )

    def _apply_source_fixes(self):
        """Idempotent in-tree rewrites (see _SOURCE_FIXES rationale)."""
        for fname, old, new, why in self._SOURCE_FIXES:
            path = os.path.join(self.source_folder, fname)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            if old in text:
                text = text.replace(old, new, 1)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                self.output.info(f"source fix applied: {fname} — {why}")
            elif new in text:
                self.output.info(f"source fix already present: {fname} — {why}")
            else:
                raise ConanInvalidConfiguration(
                    f"source fix anchor missing in {fname} ({why}) — upstream "
                    "changed; the recipe must be updated, not silently skipped"
                )

    def build(self):
        apply_conandata_patches(self)
        self._apply_source_fixes()
        # R33: compiler comes from Conan conf, never from a bare shell var.
        self.run(f"make -j1 {self._mkstr(self._make_vars())}", cwd=self.source_folder)

    def package(self):
        # Installs bin/anacron, share/man/man5|man8 and creates the spool dir
        # that the compiled-in SPOOLDIR macro points at.
        self.run(
            f"make install {self._mkstr(self._make_vars())}",
            cwd=self.source_folder,
        )

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
