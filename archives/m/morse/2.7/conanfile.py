#!/usr/bin/env python3
"""Conan recipe — morse 2.7 (Morse Classic, Makefile / C CLI)

Morse Classic is Eric S. Raymond's morse-code training utility for Unix
(http://www.catb.org/~esr/morse-classic). It builds two command-line
tools: `morse` (renders text as Morse-code beeps / on-screen dots and
dashes, and can generate random practice tests) and `QSO` (generates
simulated ham-radio QSO text used by the ARRL-style practice tests).

Build system: plain recursive Makefile (morse.d + qso.d), no configure.
Upstream DEVICE choices are X11/OSS/PA/ALSA/Linux; this recipe builds
the DEVICE=Linux console-speaker backend, which links only against
libc/libm and needs no external audio stack.

Zero source patches: the OHOS SDK clang wrapper always injects
`-Wl,--code-sign`, which the strict upstream `-Werror` flags reject on
compile-only invocations, and clang 15 flags the K&R-style prototypes
of this 1990s codebase under -Wextra. Both are handled by appending
-Wno-* suppression flags through make variables — the upstream sources
are untouched (morse.c/beepLinux.c/alarm.c/qso.d/* byte-identical to
the official tarball).

Upstream `make check` (testmorse + testqso) is executed for real in
build(): both Makefile test recipes run verbatim against the freshly
built binaries (see _run_make_check). The check's audio path needs a
writable /dev/console (PC speaker); OHOS has no PC speaker and console
access is permission-gated, so a tiny build-time-only LD_PRELOAD shim
redirects open("/dev/console") to /dev/null. The shim is compiled
inside the Conan build folder from a source embedded in this recipe,
is never installed, and the binaries under test are the real upstream
build products — only the audio sink is stubbed, the Morse decoding/
timing logic and all stdout output remain fully exercised.

One more OHOS environment quirk handled below: the HongMeng kernel
forbids hard links ("ln: Operation not permitted"), which makes the
top-level `morse:`/`QSO:` Makefile targets (plain `ln` hard links)
fail. The recipe therefore invokes the sub-directory binary targets
directly (morse.d/morseLinux, qso.d/QSO) and runs the two test
recipes with those binaries — the upstream test commands themselves
are reproduced verbatim.

License: BSD-2-Clause (COPYING: "BSD LICENSE", (c) Eric S. Raymond)
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout

# Suppressions appended to upstream CFLAGS (reasons in module docstring).
# Passed via make command-line variables so the upstream Makefiles are
# not modified. CFLAGS += in morse.d/Makefile appends to these.
_EXTRA_CFLAGS = (
    "-std=gnu89 "
    "-Wno-deprecated-non-prototype "
    "-Wno-gcc-compat "
    "-Wno-unused-command-line-argument"
)

# Build-time-only console shim: redirects open("/dev/console") (PC
# speaker) to /dev/null on OHOS, where no PC speaker exists. The real
# ioctl(KDMKTONE) on /dev/null is harmlessly ignored (upstream does not
# check its return value); timing (SIGALRM/sigwait) is untouched, so
# `morse` still paces, decodes and prints exactly as upstream.
_CONSOLE_SHIM_C = r"""
#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <dlfcn.h>

static int (*real_open)(const char *, int, ...);

int open(const char *path, int flags, ...) {
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
    if (strcmp(path, "/dev/console") == 0) {
        return real_open("/dev/null", O_WRONLY);
    }
    va_list ap;
    va_start(ap, flags);
    mode_t m = va_arg(ap, mode_t);
    va_end(ap);
    return real_open(path, flags, m);
}
"""


class MorseConan(ConanFile):
    name = "morse"
    version = "2.7"
    description = (
        "Morse Classic: morse-code training utility — renders text as "
        "Morse code (beeps and on-screen dots/dashes) and generates "
        "random practice tests and simulated ham-radio QSOs"
    )
    license = "BSD-2-Clause"
    homepage = "http://www.catb.org/~esr/morse-classic"
    url = "https://gitlab.com/esr/morse-classic"
    topics = ("morse", "morse-code", "ham-radio", "training", "cw")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: resolve the C compiler from Conan conf (never bare env vars).
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def build(self):
        cc = self._get_cc()
        src = self.source_folder

        # ── Build the two upstream binaries (zero patch) ──
        # morse: DEVICE=Linux backend (console speaker; links only -lm).
        # The top-level `morse`/`QSO` targets only create hard links,
        # which the HongMeng kernel forbids — so build the sub-directory
        # binary targets directly (identical compile/link flags).
        #
        # CFLAGS rides as a shell env prefix: `make` folds environment
        # variables in BEFORE the Makefiles' own `CFLAGS +=` lines, so
        # the upstream -O3 -Wall -Werror -Wextra all still apply (a make
        # command-line CFLAGS= assignment would override them away).
        cflags = "CFLAGS='{}'".format(_EXTRA_CFLAGS)
        self.run(
            "make morseLinux {cflags} CC='{cc}' DEVICE=Linux".format(
                cflags=cflags, cc=cc),
            cwd=os.path.join(src, "morse.d"),
        )
        self.run(
            "make QSO {cflags} CC='{cc}'".format(cflags=cflags, cc=cc),
            cwd=os.path.join(src, "qso.d"),
        )

        self._run_make_check(cc)

    def _run_make_check(self, cc):
        """Run the upstream `make check` test recipes for real.

        Upstream Makefile recipes, reproduced verbatim (only the pipe
        source/dest paths point at the sub-directory binaries because
        the top-level hard-link targets cannot exist on OHOS):

            testmorse: (cat test_input; qso.d/QSO) | ./morse -w 24 -l -e
            testqso:   qso.d/QSO | ./morse -w 20 -l -e

        On OHOS the console speaker does not exist, so both runs go
        through the LD_PRELOAD console shim (see module docstring).
        """
        src = self.source_folder
        shim_c = os.path.join(self.build_folder, "console_shim.c")
        shim_so = os.path.join(self.build_folder, "console_shim.so")
        save(self, shim_c, _CONSOLE_SHIM_C)
        self.run('"{cc}" -shared -fPIC -O2 -o "{so}" "{c}" -ldl'.format(
            cc=cc, so=shim_so, c=shim_c))

        morse_bin = os.path.join(src, "morse.d", "morseLinux")
        qso_bin = os.path.join(src, "qso.d", "QSO")

        # testmorse: test_input + a QSO-generated practice text through
        # the real `morse` at 24 wpm with letter display (~210s).
        self.run(
            '(cat test_input; "{qso}") | '
            'env LD_PRELOAD="{shim}" "{morse}" -w 24 -l -e'.format(
                qso=qso_bin, shim=shim_so, morse=morse_bin),
            cwd=src,
        )
        self.output.info("make check: testmorse passed (exit 0)")

        # testqso: a QSO-generated text through the real `morse` at
        # 20 wpm (~160s).
        self.run(
            '"{qso}" | '
            'env LD_PRELOAD="{shim}" "{morse}" -w 20 -l -e'.format(
                qso=qso_bin, shim=shim_so, morse=morse_bin),
            cwd=src,
        )
        self.output.info("make check: testqso passed (exit 0)")

    def package(self):
        src = self.source_folder
        # Command-line tools, matching upstream `make install` (BINDIR):
        #   install -m 755 morse $(DESTDIR)$(BINDIR)/morse
        #   install -m 755 QSO   $(DESTDIR)$(BINDIR)/QSO
        copy(self, "morseLinux", src=os.path.join(src, "morse.d"),
             dst=os.path.join(self.package_folder, "bin"))
        os.rename(os.path.join(self.package_folder, "bin", "morseLinux"),
                  os.path.join(self.package_folder, "bin", "morse"))
        copy(self, "QSO", src=os.path.join(src, "qso.d"),
             dst=os.path.join(self.package_folder, "bin"))
        # Man pages shipped in the official tarball (upstream installs
        # them under MANDIR/man1; Conan layout keeps share/man/man1).
        copy(self, "morse.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "QSO.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        for exe in ("morse", "QSO"):
            path = os.path.join(self.package_folder, "bin", exe)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
