#!/usr/bin/env python3
"""Conan recipe for GNU dominion 2.8.2 — turn-based strategy game + admin tools.

The tree predates OHOS in config.guess/config.sub, so configure is invoked
with --build only (GLM-19 pit #1: never pass --host with an ohos triplet to
an old config.sub) and the curses UI links against the conan-provided
ncurses. Upstream has no DESTDIR-era install; package() ships the five
built tools directly.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain

TOOLS = ["dominion", "dom_make", "dom_add", "dom_update", "dom_print"]


def _drop_umask_077(path):
    """E011/E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a temp dir (drwx--S---) that the current process cannot write.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its ./confstatXXXXXX temp dir (autoconf-2.13-era configure)."""
    if not os.path.exists(path):
        return
    data = open(path, "r", encoding="utf-8", errors="replace").read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&',
        'tmp=`mktemp -d -q "./confstatXXXXXX" 2>/dev/null` &&')
    data = data.replace(
        '(umask 077 && mkdir $tmp)',
        'mkdir $tmp')
    open(path, "w", encoding="utf-8").write(data)


_GETPASS_IMPL = '''/* OHOS adaptation: musl libc provides no getpass(); supply a minimal
   termios-based replacement (prompt on stderr, echo off, one line). */
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
static char *dom_getpass(const char *prompt)
{
    static char buf[128];
    struct termios told, tnew;
    int n;
    fprintf(stderr, "%s", prompt);
    fflush(stderr);
    if (tcgetattr(0, &told) == 0) {
        tnew = told;
        tnew.c_lflag &= ~ECHO;
        tcsetattr(0, TCSAFLUSH, &tnew);
        n = (int)read(0, buf, sizeof(buf) - 1);
        tcsetattr(0, TCSAFLUSH, &told);
    } else {
        n = (int)read(0, buf, sizeof(buf) - 1);
    }
    if (n < 0) {
        n = 0;
    }
    buf[n] = '\\0';
    if (n > 0 && buf[n - 1] == '\\n') {
        buf[n - 1] = '\\0';
    }
    return buf;
}

'''


def _patch_kr_sources(work):
    """Minimal replacements for 1995-era code that no longer compiles against
    a modern libc/ncurses, applied to the scratch copy only:
    - misc.c defines its own void getline(char[], int) which conflicts with
      POSIX getline declared by musl stdio.h (proto.h:103, misc.c:164,
      user.c:64, printmap.c:473). A global -Dgetline rename would also
      rewrite the libc declaration and still conflict, so rename dominion's
      own symbol at exactly the four sites instead.
    - conan ncurses is built opaque: WINDOW is only forward-declared, so
      cur_stuff.c's direct `->_begx/->_begy` field reads (lines 325-326,
      546-547) are replaced with the public getbegx()/getbegy() API.
    - musl has no getpass() (misc.c:190): inject a static termios-based
      dom_getpass() and point the call at it."""
    subs = {
        "proto.h": [
            ("void getline(char s[], int n);",
             "void dom_getline(char s[], int n);"),
        ],
        "misc.c": [
            ("void getline(char s[], int n)",
             "void dom_getline(char s[], int n)"),
            ("s1 = getpass(prompt);", "s1 = dom_getpass(prompt);"),
        ],
        "user.c": [
            ("getline(nation, NAMELEN);", "dom_getline(nation, NAMELEN);"),
        ],
        "printmap.c": [
            ("getline(nation, NAMELEN);", "dom_getline(nation, NAMELEN);"),
        ],
        "cur_stuff.c": [
            ("new_loc.x = sectw->_begx;", "new_loc.x = getbegx(sectw);"),
            ("new_loc.y = sectw->_begy;", "new_loc.y = getbegy(sectw);"),
            ("xfirst = sectw->_begx;", "xfirst = getbegx(sectw);"),
            ("yfirst = sectw->_begy;", "yfirst = getbegy(sectw);"),
        ],
    }
    prepends = {"misc.c": _GETPASS_IMPL}
    for fname, pairs in subs.items():
        path = os.path.join(work, fname)
        if not os.path.exists(path):
            continue
        data = open(path, "r", encoding="utf-8", errors="replace").read()
        for old, new in pairs:
            data = data.replace(old, new)
        data = prepends.get(fname, "") + data
        open(path, "w", encoding="utf-8").write(data)


class DominionConan(ConanFile):
    name = "dominion"
    version = "2.8.2"
    description = ("GNU dominion: turn-based multiplayer strategy game "
                   "(empire management) with dom_* admin tools")
    license = "GPL-1.0-only"
    homepage = "https://www.gnu.org/software/dominion/"
    url = "https://ftp.gnu.org/gnu/dominion/dominion-2.8.2.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dominion is supported only on Linux/OHOS")

    def requirements(self):
        self.requires("ncurses/6.6")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # old config.guess cannot detect the OHOS/aarch64 machine: pin build
        nc = self.dependencies["ncurses"]
        # This conan's AutotoolsToolchain reads extra_cflags into CFLAGS and
        # linker flags only from conf (CPPFLAGS carries defines alone); the
        # 1995-era Makefile LINK rule has no $(LIBS), so the -l set must ride
        # in the link flags.
        tc.extra_cflags = [
            f"-I{os.path.join(nc.package_folder, 'include')}",
        ]
        self.conf.define("tools.build:exelinkflags", [
            f"-L{os.path.join(nc.package_folder, 'lib')}",
            "-lformw", "-lmenuw", "-lpanelw", "-lncursesw",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The 1995-era config.status dies on HMDFS getcwd flakiness inside
        # the deep conan cache folders; run the in-source build from a
        # shallow scratch copy instead, then stage the binaries back.
        work = os.path.join(os.path.expanduser("~"), "tmp", "uc2",
                            f"dominion-build-{self.version}")
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".git"))
        configure = os.path.join(work, "configure")
        # E011/E114: drop umask 077 from the copied configure (HMDFS)
        _drop_umask_077(configure)
        # POSIX getline clash + opaque WINDOW reads — see _patch_kr_sources
        _patch_kr_sources(work)
        self.run(f'cd "{work}" && '
                 f'sh "{configure}" --build=aarch64-unknown-linux-gnu '
                 f'--prefix="{self.package_folder}" && make -j1')
        for tool in TOOLS:
            built = os.path.join(work, tool)
            if os.path.exists(built):
                shutil.copy2(built, os.path.join(self.source_folder, tool))

    def package(self):
        # Upstream Makefile has no DESTDIR support; ship the five tools.
        for tool in TOOLS:
            copy(self, tool, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
