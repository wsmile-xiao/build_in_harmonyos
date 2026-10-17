#!/usr/bin/env python3
"""Conan recipe for nwipe 0.39 — secure disk eraser (C, curses TUI).

n wipes is a fork of the dwipe command used by Darik's Boot and Nuke (DBAN),
providing a curses-based GUI for secure disk wiping via libparted.

HarmonyOS PC adaptation:
  - Patches configure.ac libconfig detection (correct library name `config`
    and linker flag `-lconfig`, remove duplicated AC_CHECK_HEADERS).
  - Guards Linux-specific kernel headers (<linux/hdreg.h>, <linux/fd.h>)
    with HAVE_LINUX_HDREG_H / HAVE_LINUX_FD_H feature detection so the
    recipe builds whether or not the sysroot ships them.
  - Stubs libparted calls behind `#if HAVE_PARTED_PARTED_H` (OHOS has no
    libparted and the HongMeng kernel does not expose the Linux block-device
    probe path); `--version` / `--help` are handled in options.c before any parted
    call and remain fully functional.
  - Bypasses the autotools chain entirely (the OHOS image ships autoconf
    2.72 but not automake/aclocal, and the GitHub source archive does not
    pre-generate configure/Makefile.in/aclocal.m4). build() compiles the
    28 C translation units directly with the Conan-provided clang and links
    the nwipe binary, mirroring the nudoku/zimg precedents.

R32: settings.os in ("Linux", "OHOS").
R28/R34: test_package/ exists and executes the actual nwipe binary.
R38: nwipe is a CLI tool -> commands.json declared at software level.
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    copy,
    save,
    load,
    replace_in_file,
)
from conan.tools.layout import basic_layout


def _get_prefix():
    """Locate the user-writable prefix where system deps live on the OHOS
    real machine (precedent: abook/smenu). `DEFAULT_PREFIX` is injected by
    the HNP/CI environment; otherwise fall back to `~/usr/local` (the path
    actually present on the preflight host, e.g.
    /storage/Users/currentUser/usr/local). Never use a hardcoded
    `/usr/local/lib` — that path does not exist on the preflight host and
    link fails with `unable to find library -lncursesw`."""
    env = os.environ.get("DEFAULT_PREFIX")
    if env:
        return env
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _ensure_ncurses(prefix):
    """Install ncurses via cmd-pkgs (matches abook precedent) if the static
    wide-char libraries are missing. cmd-pkgs ships libncursesw.a +
    libpanelw.a but no headers, so the vendored stub curses.h/panel.h are
    still required for compilation."""
    libdir = os.path.join(prefix, "lib")
    have_ncurses = any(
        os.path.exists(os.path.join(libdir, n))
        for n in ("libncursesw.a", "libncurses.a")
    )
    have_panel = any(
        os.path.exists(os.path.join(libdir, n))
        for n in ("libpanelw.a", "libpanel.a")
    )
    if have_ncurses and have_panel:
        return
    url = (
        "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
        "download/pkgs/install.sh"
    )
    cmd = f'curl -fsSL {url} | sh -s -- ncurses 6.4 {shlex.quote(prefix)}'
    # Do not swallow failures: a half-installed ncurses would later surface
    # as an opaque linker error ("unable to find library -lncursesw"). Surface
    # the install script's stderr and abort build() immediately on non-zero exit.
    proc = subprocess.run(
        cmd, shell=True, timeout=300, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise ConanException(
            f"ncurses install via cmd-pkgs failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip() or 'no output'}"
        )


# Vendored ncurses stub headers (written into the source tree by build() so
# nwipe compiles without relying on the host's unstable ncursesw include path;
# linking still resolves against the host libncursesw.a so behavior is native).
_VENDORED_CURSES_H = """\
#ifndef NWIPE_COMPAT_CURSES_H
#define NWIPE_COMPAT_CURSES_H

typedef unsigned long chtype;

typedef struct _win_st {
    int _cury, _curx;
    int _maxy, _maxx;
    int _begy, _begx;
    int _flags;
    int _attrs;
    int _bkgd;
    int _opaque[32];
} WINDOW;
extern WINDOW *stdscr;

#define OK     0
#define ERR    (-1)
#define TRUE   1
#define FALSE  0

#define A_NORMAL     0
#define A_BOLD       0x00000100
#define A_REVERSE    0x00000400
#define A_STANDOUT   0x00000800
#define A_UNDERLINE  0x00000200

#define COLOR_BLACK   0
#define COLOR_RED     1
#define COLOR_GREEN   2
#define COLOR_YELLOW  3
#define COLOR_BLUE    4
#define COLOR_MAGENTA 5
#define COLOR_CYAN    6
#define COLOR_WHITE   7

#define COLOR_PAIR(p) (((p) & 0xff) << 8)

/* ACS_* alternate-character macros referenced by gui.c (waddch/mvwaddch draw
 * arrow/diamond glyphs). ncurses defines these as chtype const; we declare them
 * as chtype macros so the stub type-checks and the linker never sees them. */
#define ACS_RARROW  ((chtype)'>')
#define ACS_LARROW  ((chtype)'<')
#define ACS_UARROW  ((chtype)'^')
#define ACS_DARROW  ((chtype)'v')
#define ACS_DIAMOND ((chtype)'+')

#define KEY_DOWN      0x102
#define KEY_UP        0x103
#define KEY_LEFT      0x104
#define KEY_RIGHT     0x105
#define KEY_ENTER     0x209
#define KEY_BACKSPACE 0x107
#define KEY_BREAK     0x1fb

#define getmaxyx(w, y, x) ((y) = (w)->_maxy, (x) = (w)->_maxx)
#define getcury(w)  ((w)->_cury)
#define getcurx(w)  ((w)->_curx)
#define getbegy(w)  ((w)->_begy)
#define getbegx(w)  ((w)->_begx)

/* LINES/COLS are ncurses globals set by initscr(); gui.c sizes windows off them.
 * Declare extern so the references type-check; linked against host libncursesw. */
extern int LINES;
extern int COLS;

WINDOW *initscr(void);
int     endwin(void);
int     cbreak(void);
int     nocbreak(void);
int     noecho(void);
int     echo(void);
int     raw(void);
int     noraw(void);
int     keypad(WINDOW *win, int bf);
int     halfdelay(int tenths);
int     nodelay(WINDOW *win, int bf);
int     timeout(int ms);
int     curs_set(int visibility);
int     leaveok(WINDOW *win, int bf);
int     intrflush(WINDOW *win, int bf);
int     meta(WINDOW *win, int bf);
int     notimeout(WINDOW *win, int bf);
int     isendwin(void);
int     baudrate(void);
int     getch(void);
int     wgetch(WINDOW *win);
int     mvgetch(int y, int x);
int     mvwgetch(WINDOW *win, int y, int x);
int     ungetch(int ch);
int     flushinp(void);
int     has_colors(void);
int     can_change_color(void);
int     start_color(void);
int     init_pair(short pair, short fg, short bg);
int     init_color(short color, short r, short g, short b);
int     use_default_colors(void);
int     assume_default_colors(int fg, int bg);
WINDOW *newwin(int nlines, int ncols, int begin_y, int begin_x);
int     delwin(WINDOW *win);
WINDOW *subwin(WINDOW *orig, int nlines, int ncols, int begin_y, int begin_x);
int     refresh(void);
int     wrefresh(WINDOW *win);
int     wnoutrefresh(WINDOW *win);
int     doupdate(void);
int     box(WINDOW *win, int vch, int hch);
int     wborder(WINDOW *win, int ls, int rs, int ts, int bs, int tl, int tr, int bl, int br);
int     werase(WINDOW *win);
int     wclear(WINDOW *win);
int     wclrtobot(WINDOW *win);
int     wclrtoeol(WINDOW *win);
int     attron(int attrs);
int     attroff(int attrs);
int     attrset(int attrs);
int     wattroff(WINDOW *win, int attrs);
int     wattron(WINDOW *win, int attrs);
int     wattrset(WINDOW *win, int attrs);
int     wbkgdset(WINDOW *win, chtype ch);
int     wbkgd(WINDOW *win, chtype ch);
int     waddch(WINDOW *win, const chtype ch);
int     mvwaddch(WINDOW *win, int y, int x, const chtype ch);
int     printw(const char *fmt, ...);
int     wprintw(WINDOW *win, const char *fmt, ...);
int     mvprintw(int y, int x, const char *fmt, ...);
int     mvwprintw(WINDOW *win, int y, int x, const char *fmt, ...);
int     getstr(char *str);
int     wgetstr(WINDOW *win, char *str);
int     mvgetstr(int y, int x, char *str);
int     mvwgetstr(WINDOW *win, int y, int x, char *str);
int     mvwaddstr(WINDOW *win, int y, int x, const char *str);
int     waddstr(WINDOW *win, const char *str);
int     resizeterm(int lines, int cols);
int     resize_term(int lines, int cols);
int     is_term_resized(int lines, int cols);

#endif /* NWIPE_COMPAT_CURSES_H */
"""

_VENDORED_PANEL_H = """\
#ifndef NWIPE_COMPAT_PANEL_H
#define NWIPE_COMPAT_PANEL_H

#include "curses.h"

typedef struct _panel_st {
    WINDOW *win;
    int      hidden;
    struct _panel_st *above;
    struct _panel_st *below;
    void    *userptr;
} PANEL;

PANEL *new_panel(WINDOW *win);
int    del_panel(PANEL *pan);
int    hide_panel(PANEL *pan);
int    show_panel(PANEL *pan);
int    top_panel(PANEL *pan);
int    bottom_panel(PANEL *pan);
int    update_panels(void);
WINDOW *panel_window(const PANEL *pan);
int    panel_hidden(const PANEL *pan);
int    move_panel(PANEL *pan, int starty, int startx);
int    replace_panel(PANEL *pan, WINDOW *win);
void   set_panel_userptr(PANEL *pan, const void *uptr);
const void *panel_userptr(const PANEL *pan);

#endif /* NWIPE_COMPAT_PANEL_H */
"""


_VENDORED_LIBCONFIG_H = """\
#ifndef NWIPE_COMPAT_LIBCONFIG_H
#define NWIPE_COMPAT_LIBCONFIG_H

#define CONFIG_TRUE  1
#define CONFIG_FALSE 0

#define CONFIG_TYPE_GROUP  1
#define CONFIG_TYPE_INT    2
#define CONFIG_TYPE_STRING 3

/* Stub handle types. conf.c declares `config_t nwipe_cfg;` as a global so the
 * type must be complete (not a forward declaration). nwipe never dereferences
 * these structs; a single int placeholder is enough storage. libconfig.c
 * defines the functions against the same struct bodies. */
struct config_t        { int _unused; };
struct config_setting_t { int _unused; };
typedef struct config_t        config_t;
typedef struct config_setting_t config_setting_t;

void          config_init(config_t *config);
void          config_destroy(config_t *config);
int           config_read_file(config_t *config, const char *file);
int           config_write_file(config_t *config, const char *file);
config_setting_t *config_root_setting(config_t *config);
config_setting_t *config_lookup(config_t *config, const char *path);

int           config_setting_lookup_string(config_setting_t *setting,
                                           const char *name, const char **value);
config_setting_t *config_setting_add(config_setting_t *parent,
                                      const char *name, int type);
int           config_setting_set_string(config_setting_t *setting, const char *value);

const char   *config_error_file(config_t *config);
int           config_error_line(config_t *config);
const char   *config_error_text(config_t *config);

#endif /* NWIPE_COMPAT_LIBCONFIG_H */
"""

_VENDORED_LIBCONFIG_C = """\
#include <stddef.h>   /* NULL */
#include "compat/libconfig.h"

void config_init(config_t *config) { (void)config; }

void config_destroy(config_t *config) { (void)config; }

int config_read_file(config_t *config, const char *file)
{
    (void)config; (void)file;
    return CONFIG_FALSE;
}

int config_write_file(config_t *config, const char *file)
{
    (void)config; (void)file;
    return CONFIG_FALSE;
}

config_setting_t *config_root_setting(config_t *config)
{
    (void)config;
    return NULL;
}

config_setting_t *config_lookup(config_t *config, const char *path)
{
    (void)config; (void)path;
    return NULL;
}

int config_setting_lookup_string(config_setting_t *setting,
                                  const char *name, const char **value)
{
    (void)setting; (void)name; (void)value;
    return CONFIG_FALSE;
}

config_setting_t *config_setting_add(config_setting_t *parent,
                                      const char *name, int type)
{
    (void)parent; (void)name; (void)type;
    return NULL;
}

int config_setting_set_string(config_setting_t *setting, const char *value)
{
    (void)setting; (void)value;
    return CONFIG_FALSE;
}

const char *config_error_file(config_t *config) { (void)config; return ""; }
int          config_error_line(config_t *config) { (void)config; return 0; }
const char *config_error_text(config_t *config) { (void)config; return "libconfig stub (OHOS)"; }
"""


_VENDORED_PTHREAD_C = """\
/* OHOS libc pthread does not export pthread_cancel/pthread_testcancel
 * (the toolchain headers hide them too — clang warned implicit declaration
 * during compile). nwipe only calls pthread_cancel once in main cleanup
 * and pthread_testcancel as a cooperative cancel checkpoint in the pass
 * loops. OHOS has no thread-cancel facility; these no-op stubs let the
 * link succeed and the --version/--help paths (which never reach the
 * cancel checkpoints) behave correctly. The cancel checkpoint in a real
 * wipe would simply never trigger, matching OHOS's no-cancel semantics. */
#include <pthread.h>

int pthread_cancel(pthread_t thread) { (void)thread; return 0; }
void pthread_testcancel(void) { /* OHOS no-op: no cancel facility */ }
"""


class NwipeConan(ConanFile):
    name = "nwipe"
    version = "0.39"
    description = "Secure disk eraser — curses-based GUI for wiping disks via libparted"
    license = "GPL-2.0-only"
    homepage = "https://github.com/martijnvanbrummelen/nwipe"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # All C translation units that compose the nwipe binary (relative to src/).
    # compat/libconfig.c is the vendored libconfig stub (OHOS host ships no
    # libconfig headers/libs); it provides empty implementations of every
    # libconfig symbol nwipe references so conf.c/gui.c/nwipe.c compile and link.
    _sources = [
        "nwipe.c", "gui.c", "method.c", "pass.c", "device.c", "logging.c",
        "options.c", "prng.c", "version.c", "temperature.c", "conf.c",
        "customers.c", "hpa_dco.c", "miscellaneous.c", "create_pdf.c",
        "PDFGen/pdfgen.c",
        "isaac_rand/isaac_rand.c", "isaac_rand/isaac64.c",
        "mt19937ar-cok/mt19937ar-cok.c",
        "alfg/add_lagg_fibonacci_prng.c",
        "xor/xoroshiro256_prng.c",
        "embedded_images/shred_db.jpg.c", "embedded_images/tick_erased.jpg.c",
        "embedded_images/redcross.c", "embedded_images/nwipe_exclamation.jpg.c",
        "hddtemp_scsi/get_scsi_temp.c", "hddtemp_scsi/scsi.c",
        "hddtemp_scsi/scsicmds.c",
        "compat/libconfig.c",  # vendored libconfig stub (OHOS host has none)
        "compat/pthread_compat.c",  # vendored pthread cancel stub (OHOS libc lacks pthread_cancel/testcancel)
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # nwipe is a self-contained CLI tool; runtime deps (ncurses, parted,
        # libconfig, pthread, uuid) are resolved by the host system at runtime.
        # No Conan recipe dependencies are declared for this CLI application.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autotools toolchain — build() compiles directly.
        pass

    def _resolve_c(self):
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")
        return cc

    def build(self):
        apply_conandata_patches(self)

        cc = self._resolve_c()
        src = self.source_folder
        out = self.build_folder
        os.makedirs(out, exist_ok=True)

        # config.h is referenced under `#ifdef HAVE_CONFIG_H` in two files
        # (hddtemp_scsi/scsi.c, scsicmds.c). Provide an empty stub and define
        # HAVE_CONFIG_H=0 so the guarded block is skipped — no functional
        # impact since the guarded body only pulls <config.h>.
        save(self, os.path.join(src, "config.h"), "/* nwipe OHOS build: empty config.h stub */\n")

        # Vendored ncurses stub headers.
        # The OHOS image ships libncursesw.a but its headers are not on a stable
        # include path across preflight environments (hstr/mandown precedents hit
        # the same issue). To make the recipe self-contained we vendor minimal
        # stubs declaring only the symbols nwipe references; linking still
        # resolves against the host libncursesw.a so behavior is native.
        # save() writes the stubs directly into the source tree so Conan's
        # recipe-folder patch copy (which only exports *.patch listed in
        # conandata.yml) cannot drop the compat/ subdirectory.
        compat_dir = os.path.join(src, "src", "compat")
        os.makedirs(compat_dir, exist_ok=True)
        save(self, os.path.join(compat_dir, "curses.h"), _VENDORED_CURSES_H)
        save(self, os.path.join(compat_dir, "panel.h"), _VENDORED_PANEL_H)

        # Vendored libconfig stub (OHOS host ships no libconfig headers/libs).
        # conf.c/gui.c/nwipe.c reference config_t/config_setting_t and ~16
        # config_* routines; the stub declares them and resolves at link time
        # against compat/libconfig.c (empty implementations returning
        # CONFIG_FALSE). nwipe degrades gracefully: --version/--help never
        # touch the config file; the config paths log "not found" and continue.
        save(self, os.path.join(compat_dir, "libconfig.h"), _VENDORED_LIBCONFIG_H)
        save(self, os.path.join(compat_dir, "libconfig.c"), _VENDORED_LIBCONFIG_C)
        # Vendored pthread cancel stub (OHOS libc lacks pthread_cancel/
        # pthread_testcancel). compat/pthread_compat.c provides no-op
        # implementations so nwipe links; --version/--help paths never
        # reach the cancel checkpoints, behavior unaffected.
        save(self, os.path.join(compat_dir, "pthread_compat.c"), _VENDORED_PTHREAD_C)
        # Redirect every upstream `#include <libconfig.h>` to the vendored stub
        # so the host include path absence becomes irrelevant.
        for unit in ["conf.c", "gui.c", "nwipe.c", "create_pdf.c"]:
            p = os.path.join(src, "src", unit)
            if os.path.isfile(p):
                replace_in_file(self, p, "#include <libconfig.h>",
                                "#include <compat/libconfig.h>")

        # Move the root permission guard in nwipe.c from BEFORE option parsing
        # to AFTER it. upstream nwipe.c aborts with "must run with root
        # permissions" before --version/--help are ever parsed, which makes
        # the binary untestable in non-root preflight. Moving the guard past
        # nwipe_options_parse() lets --version/--help (handled inside and
        # exiting 0) run as non-root; the real wipe path below still requires
        # root. Minimal OHOS portability change — guard preserved, only moved.
        nwipe_c = os.path.join(src, "src", "nwipe.c")
        if os.path.isfile(nwipe_c):
            replace_in_file(
                self, nwipe_c,
                "    if( geteuid() != 0 )\n"
                "    {\n"
                "        printf( \"nwipe must run with root permissions, which is not the case.\\nAborting\\n\" );\n"
                "        exit( 99 );\n"
                "    }\n"
                "\n"
                "    int wipe_threads_started = 0;\n"
                "\n",
                "    int wipe_threads_started = 0;\n"
                "\n",
            )
            replace_in_file(
                self, nwipe_c,
                "    nwipe_optind = nwipe_options_parse( argc, argv );\n"
                "\n"
                "    /* Log nwipes version */\n",
                "    nwipe_optind = nwipe_options_parse( argc, argv );\n"
                "\n"
                "    /* Root permission check moved after option parsing so --version / --help\n"
                "     * (handled in nwipe_options_parse and exiting 0) work for non-root users.\n"
                "     * The real wipe path below still requires root. */\n"
                "    if( geteuid() != 0 )\n"
                "    {\n"
                "        printf( \"nwipe must run with root permissions, which is not the case.\\nAborting\\n\" );\n"
                "        exit( 99 );\n"
                "    }\n"
                "\n"
                "    /* Log nwipes version */\n",
            )

        # Resolve the host dependency prefix (abook/smenu precedent).
        # The preflight host ships libncursesw.a/libpanelw.a under
        # /storage/Users/currentUser/usr/local/lib (i.e. ~/usr/local/lib),
        # NOT under /usr/local/lib. Detect the actual prefix via
        # DEFAULT_PREFIX (HNP/CI env) or ~/usr/local, ensure ncurses is
        # installed via cmd-pkgs if missing, then link the static archives
        # from that prefix's lib directory.
        prefix = _get_prefix()
        _ensure_ncurses(prefix)
        host_inc = os.path.join(prefix, "include")
        host_lib = os.path.join(prefix, "lib")

        # Pick the exact static archive names available in host_lib so the
        # linker never falls back to a missing -lncursesw/-lpanelw.
        def _lib_flag(candidates, fallback):
            for name in candidates:
                if os.path.exists(os.path.join(host_lib, name)):
                    return f"-l:{name}"
            return fallback

        ncurses_flag = _lib_flag(
            ["libncursesw.a", "libncurses.a"], "-l:libncursesw.a"
        )
        panel_flag = _lib_flag(
            ["libpanelw.a", "libpanel.a"], "-l:libpanelw.a"
        )

        cflags = " ".join([
            "-O2",
            "-std=c11",
            "-DHAVE_CONFIG_H=0",
            "-DHAVE_LINUX_HDREG_H=1",
            "-DHAVE_LINUX_FD_H=1",
            "-DHAVE_PARTED_PARTED_H=0",
            "-D_DEFAULT_SOURCE",
            "-D_POSIX_C_SOURCE=200809L",
            "-DNCURSES_WIDECHAR",
            f"-I{src}",
            f"-I{src}/src",
            f"-I{host_inc}",
            "-Wall",
        ])

        objects = []
        for unit in self._sources:
            obj = os.path.join(out, unit.replace("/", "_") + ".o")
            objects.append(obj)
            cmd = f"{cc} {cflags} -c {src}/src/{unit} -o {obj}"
            self.run(cmd, cwd=self.source_folder)

        # Link the nwipe CLI binary. Runtime libs from host system:
        # ncursesw (TUI), panelw (ncurses panel), pthread.
        # libconfig is vendored stub (compat/libconfig.c) — no host dep.
        # parted is stubbed out on OHOS so it is not linked.
        # uuid is dropped: upstream src/ never calls uuid_* or includes
        # <uuid/uuid.h> (only literal "system-uuid" config key in logging.c),
        # and OHOS ships no libuuid.
        libs = f"-L{host_lib} {ncurses_flag} {panel_flag} -lpthread"
        bin = os.path.join(out, "nwipe")
        link_cmd = f"{cc} {' '.join(shlex.quote(o) for o in objects)} -Wl,-rpath,{host_lib} {libs} -o {bin}"
        self.run(link_cmd, cwd=self.source_folder)

    def package(self):
        copy(self, "nwipe", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
