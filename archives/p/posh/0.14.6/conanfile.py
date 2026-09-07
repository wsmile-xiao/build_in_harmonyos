#!/usr/bin/env python3
"""Conan recipe for posh 0.14.6 — Policy-compliant Ordinary SHell.

posh is a stripped-down derivative of pdksh that aims at full POSIX
compliance (Debian maintained).  It ships a single binary, `posh`, plus
its man page; there are no libraries and no external dependencies
(the W0 preflight found zero runtime requirements).

OHOS adaptation notes (see also notes.md):
  * The release tarball ships NO pre-generated configure (Debian builds
    it with `autoreconf -fi` via debian/rules), so build() bootstraps
    the autotools machinery itself.  The CI sandbox has the autoconf
    suite under /data/service/hnp/bin but lacks automake/aclocal, hence
    the `automake/1.18` tool_requires (abiword-plugin/adplay precedent).
    posh does not use libtool (no LT_INIT, plain bin_PROGRAMS).
  * The config.guess/config.sub that autoreconf installs come from the
    conan `automake/1.18` package — the pristine GNU versions.  On this
    platform they need two portability fixes, applied in build() right
    after autoreconf (both files are *generated* here, absent from the
    tarball, so they cannot ship as regular patches):
      - E011/E114: `(umask 077 && mktemp -d ...)` temp dirs are not
        writable on HMDFS (UID-mapped setgid), so config.status and
        config.guess both die — umask 077 is relaxed to 022 (configure)
        / 000 (config.guess, as upstream had before the 2024-07-27
        hardening) — poke 0001 patch approach, applied at generation
        time;
      - E007: the GNU config.guess/config.sub know nothing about
        HarmonyOS — the `*:HarmonyOS:*:*` uname branch, the __OHOS__
        LIBC probe, the ohos-linux triplet and the ohos* OS entry are
        inserted (same change set as the E007 knowledge entry /
        patch-autotools-ohos.pl).  R8 note: the __OHOS__ LIBC probe
        inside config.guess is the sanctioned platform-macro exception
        (libc detection cannot be done differently there).
  * Upstream quirk (intentionally NOT fixed): acinclude.m4 still defines
    POSH_VERSION=0.14.5 — the maintainer forgot to bump it for the
    0.14.6 release, so the binary reports $POSH_VERSION=0.14.5.  This
    matches upstream's own tests/version.t expectation and is kept
    as-is for upstream fidelity.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# E007: HarmonyOS uname branch for config.guess (matches the OHOS-adapted
# automake shipped on the devices; inserted before *:NetBSD:*:*).
_HARMONYOS_GUESS_BLOCK = """    *:HarmonyOS:*:*)
\tcase "$UNAME_MACHINE" in
\t    aarch64|arm64) MACHINE=aarch64 ;;
\t    armv7*|armv8*) MACHINE=arm ;;
\t    x86_64|amd64)  MACHINE=x86_64 ;;
\t    i?86)         MACHINE=i686 ;;
\t    *)            MACHINE="$UNAME_MACHINE" ;;
\tesac
\tGUESS=${MACHINE}-unknown-linux-ohos
\t;;

"""


class PoshConan(ConanFile):
    name = "posh"
    version = "0.14.6"
    description = "posh — Policy-compliant Ordinary SHell, a stripped-down pdksh derivative aiming at POSIX compliance (Debian maintained)"
    license = "GPL-3.0-only", "BSD-3-Clause", "Public Domain"
    homepage = "https://salsa.debian.org/debian/posh"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # No-op today (patches: {} — zero source modifications), kept so
        # any future patch added to conandata.yml is exported correctly.
        export_conandata_patches(self)

    def build_requirements(self):
        # The tarball ships no configure: build() must run `autoreconf -fi`
        # to bootstrap.  The CI sandbox / minimal OHOS image lacks
        # automake/aclocal (only the autoconf suite is present under
        # /data/service/hnp/bin), so pull automake in as a tool_requires
        # (abiword-plugin/adplay precedent).  posh does not use libtool.
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler/flags come from the Conan toolchain
        # (AutotoolsToolchain reads the profile conf), never from bare
        # CC/CFLAGS shell variables.
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()

    # ---- generated-autotools-scripts portability fixes -----------------

    def _fix_configure_umask(self, configure):
        # E011/E114: `(umask 077 && mktemp -d ...)` creates a 0700 temp
        # dir that HMDFS turns into an unwritable drwx--S--- dir, so
        # config.status cannot write subs1.awk ("could not setup config
        # files machinery").  Relax to 022 — poke 0001 patch approach,
        # applied to the freshly generated configure (the tarball does
        # not ship one, so this cannot be a regular patch).
        with open(configure, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        n = data.count("umask 077")
        if n:
            data = data.replace("umask 077", "umask 022")
            with open(configure, "w", encoding="utf-8") as f:
                f.write(data)
        return n

    def _fix_config_guess_sub(self, src):
        """E007 + E011 fixes for the config.guess/config.sub that
        autoreconf just installed from the conan automake package
        (pristine GNU versions: no HarmonyOS support, umask 077 temp
        dirs).  Same change set as knowledge entry E007 /
        patch-autotools-ohos.pl, implemented as idempotent in-recipe
        rewrites because these files are generated (absent from the
        tarball) and cannot ship as patches.

        E011 (config.guess flavour): on HMDFS `umask 077 && mktemp -d`
        yields a drwx--S--- dir that is not writable even by its owner
        (verified: umask 022 -> drwxr-s--x writable, 077 -> 0700-mapped
        unwritable), so config.guess cannot create dummy.c and dies
        with "unable to guess system type".  All umask 077 occurrences
        are relaxed to 000 — the value upstream used before the
        2024-07-27 hardening."""
        guess = os.path.join(src, "config.guess")
        sub = os.path.join(src, "config.sub")
        notes = []

        if os.path.isfile(guess):
            with open(guess, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            n = data.count("umask 077")
            if n:
                data = data.replace("umask 077", "umask 000")
            # E007: __OHOS__ LIBC probe after the __ANDROID__ one.
            if "__OHOS__" not in data:
                data = re.sub(
                    r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                    "\\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    data, count=1, flags=re.MULTILINE)
            # E007: HarmonyOS uname branch before the NetBSD one.
            if "HarmonyOS" not in data:
                data = re.sub(
                    r"(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)",
                    lambda m: _HARMONYOS_GUESS_BLOCK + m.group(1),
                    data, count=1, flags=re.MULTILINE)
            with open(guess, "w", encoding="utf-8") as f:
                f.write(data)
            notes.append(
                f"config.guess: umask fixes={n}, "
                f"__OHOS__={'__OHOS__' in data}, "
                f"HarmonyOS={'HarmonyOS' in data}")

        if os.path.isfile(sub):
            with open(sub, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            # E007: ohos-linux triplet after the android-linux one.
            if "ohos-linux)" not in data:
                data = re.sub(
                    r"(\s*android-linux\)\s*\n)((\s*)basic_machine=\$field1-unknown\s*\n)((\s*)basic_os=linux-android\s*\n)(\s*;;\s*\n)",
                    lambda m: (m.group(1) + m.group(2) + m.group(4)
                               + m.group(6) + "\tohos-linux)\n"
                               + m.group(3) + "basic_machine=$field1-unknown\n"
                               + m.group(5) + "basic_os=linux-ohos\n"
                               + m.group(6)),
                    data, count=1)
            # E007: ohos* in the OS type list.
            if "ohos*" not in data:
                data = re.sub(r"(gnu\*\s*\|\s*android\*)",
                              lambda m: m.group(1) + " | ohos*",
                              data, count=1)
            with open(sub, "w", encoding="utf-8") as f:
                f.write(data)
            notes.append(
                f"config.sub: ohos-linux={'ohos-linux)' in data}, "
                f"ohos*={'ohos*' in data}")

        for note in notes:
            self.output.info(f"autotools script fix: {note}")
        # Fail loudly if the essential E007 markers did not land: a
        # silent miss would resurface as "cannot guess build type".
        for path, marker in ((guess, "HarmonyOS"), (sub, "ohos-linux)")):
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    if marker not in f.read():
                        raise ConanException(
                            f"E007 fix did not land in {path} "
                            f"(marker {marker!r} missing) — aborting "
                            "before configure fails obscurely")

    def build(self):
        # No-op today (patches: {} — zero source modifications); kept so
        # any future patch declared in conandata.yml is applied here.
        apply_conandata_patches(self)
        # Bootstrap: the tarball has no configure (Debian uses
        # `autoreconf -fi` in debian/rules).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # Portability fixes on the freshly generated autotools scripts
        # (see the class docstring; they are generated files, so the
        # fixes live here instead of patches/).
        fixed = self._fix_configure_umask(
            os.path.join(self.source_folder, "configure"))
        if fixed:
            self.output.info(
                "relaxed umask 077 -> 022 in generated configure "
                f"({fixed} occurrence(s), E011/E114)")
        self._fix_config_guess_sub(self.source_folder)

        autotools = Autotools(self)
        # No --build/--host: config.guess (E007-fixed above) detects
        # aarch64-unknown-linux-ohos natively.
        autotools.configure()
        # E074 avoidance: parallel make can hit the HMDFS jobserver fifo
        # EPERM (abiword-plugin precedent); posh is tiny, -j1 is free.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Application package: a single executable in bin/, no libs.
        self.cpp_info.bindirs = ["bin"]
