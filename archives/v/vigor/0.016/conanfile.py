"""Conan recipe for vigor 0.016 — a vi-compatible editor with a Tcl/Tk GUI
(an nvi variant).

Build notes (match the locally-verified manual configure+make):

* Vigor REQUIRES Tcl/Tk at configure time: configure.in hard-fails
  (AC_MSG_ERROR) unless Tcl_Init/Tk_Init can be linked.  Tk pulls in X11.
* nvi's bundled curses / DB / regex are used (--enable-curses --enable-db
  --enable-re), exactly as the successful manual build did.
* HarmonyOS PC has no system libtermlib/libtermcap, and linking ncurses'
  static libncursesw.a would drag its full curses global state into the
  binary (duplicate-symbol link errors with the bundled curses).  A minimal
  termcap(3) shim (built-in VT100 entry) is therefore compiled into
  libtermlib.a inside a build-folder private prefix (R49) and injected via
  LDFLAGS, so configure's AC_CHECK_LIB(termlib,tgetent) succeeds and the
  editor can drive a standard ANSI terminal.
* ncurses is required headers/runtime-only (libs=False): its curses.h is
  consulted by configure's tigetstr/setupterm probes and its TERMINFO tree is
  exported for consumers, but its static libraries are never linked into the
  vigor binary.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


TERMCAP_SHIM_SOURCE = r'''
/*
 * Minimal termcap(3) implementation for HarmonyOS PC.
 *
 * nvi/vigor 0.016's bundled curses requires the classic termcap API
 * (tgetent / tgetstr / tgetnum / tgetflag / tgoto / tputs).
 * HarmonyOS PC has no system libtermcap/libtermlib, and pulling in
 * ncurses' static libncursesw.a drags its full curses global state
 * (stdscr/curscr/COLS/setupterm/cbreak/raw/...) which clashes with
 * the nvi bundled curses (duplicate-symbol link errors).
 *
 * This shim implements the termcap protocol and ships a built-in
 * VT100-compatible entry so the editor can drive a standard ANSI
 * terminal.  The implementation is functional: capabilities are
 * decoded from the termcap entry copied by tgetent(), tgoto()
 * expands cursor addressing, tputs() emits strings with padding.
 */

#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <stdio.h>

static const char builtin_termcap[] =
	"vt100|vt102|vt220|ansi|dumb|xx:"
	"am:bs:"
	"cm=\\E[%i%d;%dH:"
	"up=\\E[A:do=\\E[B:nd=\\E[C:le=\\E[D:"
	"ho=\\E[H:cl=\\E[H\\E[J:cd=\\E[J:ce=\\E[K:"
	"so=\\E[7m:se=\\E[m:us=\\E[4m:ue=\\E[m:md=\\E[1m:me=\\E[m:"
	"cr=\\r:nl=\\n:ta=\\t:"
	"vs=\\E[?25h:ve=\\E[?25l:"
	"kh=\\E[H:kl=\\E[D:kr=\\E[C:ku=\\E[A:kd=\\E[B:"
	"k0=\\E[10~:k1=\\E[11~:k2=\\E[12~:k3=\\E[13~:k4=\\E[14~:"
	"k5=\\E[15~:k6=\\E[17~:k7=\\E[18~:k8=\\E[19~:k9=\\E[20~:"
	"co#80:li#24:";

int
tgetent(char *bp, const char *name)
{
	size_t n;

	if (bp == NULL)
		return (-1);
	(void)name;
	n = strlen(builtin_termcap) + 1;
	if (n > 1024)
		n = 1024;
	memcpy(bp, builtin_termcap, n - 1);
	bp[n - 1] = '\0';
	return (1);
}

char *
tgetstr(char *id, char **area)
{
	const char *p;
	char *dst, *begin;

	if (id == NULL || id[0] == '\0' || id[1] == '\0')
		return (NULL);
	p = builtin_termcap;
	while (*p != '\0') {
		while (*p != '\0' && *p != ':')
			p++;
		if (*p == '\0')
			break;
		p++;
		if (*p == '\0')
			break;
		if (p[0] == id[0] && p[1] == id[1] && p[2] == '=') {
			p += 3;
			if (area == NULL || *area == NULL)
				return (NULL);
			dst = begin = *area;
			while (*p != '\0' && *p != ':') {
				if (*p == '\\') {
					p++;
					if (*p == '\0')
						break;
					switch (*p) {
					case 'E': *dst++ = '\033'; p++; break;
					case 'n': *dst++ = '\n'; p++; break;
					case 'r': *dst++ = '\r'; p++; break;
					case 't': *dst++ = '\t'; p++; break;
					case 'b': *dst++ = '\b'; p++; break;
					case 'f': *dst++ = '\f'; p++; break;
					case '^':
						if (p[1] != '\0') {
							*dst++ = (char)(p[1] & 0x1f);
							p += 2;
						} else {
							*dst++ = '^';
							p++;
						}
						break;
					default:
						*dst++ = *p++;
						break;
					}
				} else
					*dst++ = *p++;
			}
			*dst = '\0';
			*area = dst + 1;
			return (begin);
		}
	}
	return (NULL);
}

int
tgetnum(char *id)
{
	const char *p;

	if (id == NULL || id[0] == '\0' || id[1] == '\0')
		return (-1);
	p = builtin_termcap;
	while (*p != '\0') {
		while (*p != '\0' && *p != ':')
			p++;
		if (*p == '\0')
			break;
		p++;
		if (*p == '\0')
			break;
		if (p[0] == id[0] && p[1] == id[1] && p[2] == '#')
			return (atoi(p + 3));
	}
	return (-1);
}

int
tgetflag(char *id)
{
	const char *p;

	if (id == NULL || id[0] == '\0' || id[1] == '\0')
		return (0);
	p = builtin_termcap;
	while (*p != '\0') {
		while (*p != '\0' && *p != ':')
			p++;
		if (*p == '\0')
			break;
		p++;
		if (*p == '\0')
			break;
		if (p[0] == id[0] && p[1] == id[1] &&
		    (p[2] == ':' || p[2] == '\0'))
			return (1);
	}
	return (0);
}

char *
tgoto(const char *cm, int col, int row)
{
	static char out[128];
	char *q = out;
	int incr = 0, next = 0, val;
	const char *p;

	if (cm == NULL)
		return ("OOPS");
	for (p = cm; *p != '\0' && q < out + sizeof(out) - 1; p++) {
		if (*p != '%') {
			*q++ = *p;
			continue;
		}
		p++;
		switch (*p) {
		case 'i': incr = 1; break;
		case 'r': { int t = col; col = row; row = t; break; }
		case 'n': col ^= 0x20; row ^= 0x20; break;
		case 'd':
			val = (next == 0 ? col : row) + incr;
			next ^= 1;
			q += sprintf(q, "%d", val);
			break;
		case '2':
			val = (next == 0 ? col : row) + incr;
			next ^= 1;
			if (val < 0) val = 0;
			if (val > 99) val = 99;
			*q++ = '0' + val / 10;
			*q++ = '0' + val % 10;
			break;
		case '3':
			val = (next == 0 ? col : row) + incr;
			next ^= 1;
			if (val < 0) val = 0;
			if (val > 999) val = 999;
			*q++ = '0' + val / 100;
			*q++ = '0' + (val / 10) % 10;
			*q++ = '0' + val % 10;
			break;
		case '+':
			val = (next == 0 ? col : row) + incr;
			next ^= 1;
			*q++ = (char)(val + p[1]);
			if (p[1] != '\0')
				p++;
			break;
		case '.':
			val = (next == 0 ? col : row) + incr;
			next ^= 1;
			*q++ = (char)(val + 32);
			break;
		case 'B':
			val = (next == 0 ? col : row) + incr;
			next ^= 1;
			val = ((val / 10) << 4) + (val % 10);
			*q++ = (char)val;
			break;
		case '%': *q++ = '%'; break;
		case '\0': goto done;
		default: break;
		}
	}
done:
	*q = '\0';
	return (out);
}

int
tputs(const char *str, int affcnt, int (*putc)(int))
{
	(void)affcnt;
	if (str == NULL)
		return (0);
	if (*str == '$' && str[1] == '<') {
		str += 2;
		while (isdigit((unsigned char)*str))
			str++;
		if (*str == '>')
			str++;
	}
	while (*str != '\0')
		putc((unsigned char)*str++);
	return (0);
}
'''


class VigorConan(ConanFile):
    name = "vigor"
    version = "0.016"
    description = ("Vigor — a vi-compatible editor with a Tcl/Tk interface "
                   "(a hack layered on top of nvi)")
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/vigor/"
    url = "https://sourceforge.net/projects/vigor/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("tcl/9.0.3.2")
        self.requires("tk/9.0.3.2")
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")
        self.requires("ncurses/6.4", libs=False)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vigor is supported only on Linux/OHOS, not {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _privlib_dir(self):
        return os.path.join(self.build_folder, "prefix", "lib")

    def _resolve_cc(self):
        """R33 + DRAFT-9639: the profile's tools.build:compiler_executables
        hardcodes the CI worker layout (/data/service/hnp/bin/clang).  That
        path is only guaranteed on the CI runner; when it does not exist
        locally, fall back to a PATH-resolved clang (the profile's buildenv
        already puts the real toolchain bin/ first on PATH)."""
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        if not os.path.isfile(cc):
            cc = shutil.which("clang") or cc
        return cc

    def _build_termcap_shim(self):
        """Compile the built-in-VT100 termcap shim into libtermlib.a under the
        build-folder private prefix.  configure's AC_CHECK_LIB(termlib,tgetent)
        needs a linkable -ltermlib; the final binary needs tgetent/tgetstr/
        tgetnum/tgetflag/tgoto/tputs for the bundled curses."""
        privlib = self._privlib_dir()
        os.makedirs(privlib, exist_ok=True)
        src = os.path.join(self.build_folder, "termcap_shim.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write(TERMCAP_SHIM_SOURCE)
        cc = self._resolve_cc()
        obj = os.path.join(privlib, "termcap_shim.o")
        self.run(f"{cc} -c -O2 {src} -o {obj}", cwd=self.build_folder)
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.run(f"{ar} rcs {os.path.join(privlib, 'libtermlib.a')} {obj}",
                 cwd=self.build_folder)

    def _link_tcl_tk_symlinks(self):
        """configure.in probes -ltcl/-ltk and the versioned aliases
        (tcl82/tcl8.2/tcl80/tcl8.0).  The tcl/tk packages ship libtcl9.0.so /
        libtcl9tk9.0.so; expose unversioned symlinks in the private prefix so
        every probe candidate resolves regardless of environment LIBS."""
        privlib = self._privlib_dir()
        os.makedirs(privlib, exist_ok=True)
        tcl_lib = self.dependencies["tcl"].cpp_info.libdirs[0]
        tk_lib = self.dependencies["tk"].cpp_info.libdirs[0]
        tcl_real = os.path.join(tcl_lib, "libtcl9.0.so")
        tk_real = os.path.join(tk_lib, "libtcl9tk9.0.so")
        for name in ("libtcl.so", "libtcl8.0.so", "libtcl8.2.so",
                     "libtcl80.so", "libtcl82.so"):
            link = os.path.join(privlib, name)
            if not os.path.lexists(link):
                os.symlink(tcl_real, link)
        for name in ("libtk.so", "libtk8.0.so", "libtk8.2.so",
                     "libtk80.so", "libtk82.so"):
            link = os.path.join(privlib, name)
            if not os.path.lexists(link):
                os.symlink(tk_real, link)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-curses",   # nvi bundled curses
            "--enable-db",       # nvi bundled DB
            "--enable-re",       # nvi bundled regex
        ])
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--host=aarch64-linux-ohos",
                "--build=aarch64-linux-ohos",
            ])
        tc.extra_ldflags.append("-L" + self._privlib_dir())
        env = tc.environment()
        env.define("vi_cv_path_preserve",
                   os.path.join(self.build_folder, "vi_preserve", "vi.recover"))
        x11 = self.dependencies["libx11"].cpp_info
        x11_inc = x11.includedirs[0]
        x11_lib = x11.libdirs[0]
        env.define("ac_cv_have_x",
                   "have_x=yes ac_x_includes=%s ac_x_libraries=%s"
                   % (x11_inc, x11_lib))
        cc = self._resolve_cc()
        env.define("ac_cv_prog_CPP", f"{cc} -E -Qunused-arguments")
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        tc.generate(env=env)

    def _patch_buildenv_shells(self):
        """E540/DRAFT-9639 companion: the profile's [buildenv] hardcodes
        CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash and the toolchain env
        hardcodes CC/CXX=/data/service/hnp/bin/clang{++,} (CI worker layout).
        autoconf 2.13 runs `${CONFIG_SHELL-/bin/sh} $ac_config_sub sun4` to
        validate config.sub, and the compiler check runs `${CC} ...`; when the
        /data/service/hnp tree is not mounted (shadow-CI transient) those
        binaries are missing and configure aborts ("can not run config.sub",
        "C compiler cannot create executables").  Patch the generated env
        scripts to PATH-resolved tools only when the CI paths are absent
        (keeps the CI values when they exist).  Called from build() because
        the env scripts are generated after generate() returns."""
        gens = self.generators_folder
        if not os.path.isdir(gens):
            return
        for fname in os.listdir(gens):
            if not fname.endswith(".sh"):
                continue
            path = os.path.join(gens, fname)
            data = open(path, encoding="utf-8").read()
            new_shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
            for var in ("CONFIG_SHELL", "SHELL"):
                for m in re.finditer(r'export %s="([^"]*)"' % var, data):
                    if not os.path.isfile(m.group(1)):
                        data = data.replace(m.group(0),
                                            'export %s="%s"' % (var, new_shell))
            for var, key, fallback in (("CC", "c", "clang"),
                                       ("CXX", "cpp", "clang++")):
                for m in re.finditer(r'export %s="([^"]*)"' % var, data):
                    if not os.path.isfile(m.group(1)):
                        comp = self.conf.get("tools.build:compiler_executables",
                                             default={}, check_type=dict)
                        alt = comp.get(key) or fallback
                        if not os.path.isfile(alt):
                            alt = shutil.which(fallback) or alt
                        data = data.replace(m.group(0),
                                            'export %s="%s"' % (var, alt))
            # deps env: AutotoolsDeps ignores the `libs=False` requirement
            # trait and still emits -lformw -lmenuw -lpanelw -lncursesw (from
            # the ncurses package cpp_info).  Linking those static archives
            # duplicates the termcap shim + nvi bundled curses symbols
            # (tputs/tgetent/keypad/...), so strip them from LIBS exactly like
            # the verified manual build (which linked only -ltermlib -ltk
            # -ltcl -ldl -lm -lX11; ncurses is headers+TERMINFO only).
            if fname.startswith("conanautotoolsdeps"):
                data = re.sub(
                    r'(export LIBS="[^"]*?)-lformw -lmenuw -lpanelw -lncursesw(.*")',
                    r'\1\2', data, count=1)
            open(path, "w", encoding="utf-8").write(data)

    def build(self):
        apply_conandata_patches(self)
        self._flatten_upstream_build_dir()
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                       "ac_unique_file=../common/main.c",
                       "ac_unique_file=common/main.c")
        makefile_in = os.path.join(self.source_folder, "Makefile.in")
        if os.path.exists(makefile_in):
            replace_in_file(self, makefile_in,
                            "srcdir=\t@srcdir@/..",
                            "srcdir=\t@srcdir@")
        if self.settings.os == "OHOS":
            config_sub = os.path.join(self.source_folder, "config.sub")
            replace_in_file(self, config_sub,
                            "tahoe | i[345]86 | i860 | m68k | m68000 | m88k | ns32k | arm \\",
                            "tahoe | i[345]86 | i860 | m68k | m68000 | m88k | ns32k | arm | aarch64 \\")
            replace_in_file(self, config_sub,
                            "| sparc-* | ns32k-* | fx80-* | arm-* | c[123]* \\",
                            "| sparc-* | ns32k-* | fx80-* | arm-* | aarch64-* | c[123]* \\")
            replace_in_file(self, config_sub,
                            "| -udi* | -eabi* | -lites* )",
                            "| -udi* | -eabi* | -lites* | -ohos* )")
        for f in ("configure", "config.guess", "config.sub", "install-sh"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.chmod(p, 0o755)
        self._build_termcap_shim()
        self._link_tcl_tk_symlinks()
        self._patch_buildenv_shells()
        os.makedirs(os.path.join(self.build_folder, "vi_preserve", "vi.recover"),
                    exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        for name in ("Makefile.in", "config.h.in", "configure"):
            src = os.path.join(self.source_folder, name)
            if os.path.exists(src) and not os.path.exists(
                    os.path.join(self.build_folder, name)):
                shutil.copy2(src, os.path.join(self.build_folder, name))
        autotools.make(args=["-j1"])

    def _flatten_upstream_build_dir(self):
        """Move the contents of the upstream `build/` subdir into the source
        root (configure, Makefile.in, aclocal.m4, config.*, install-sh, ...)."""
        src = self.source_folder
        build_sub = os.path.join(src, "build")
        if not os.path.isdir(build_sub):
            return
        for name in sorted(os.listdir(build_sub)):
            s = os.path.join(build_sub, name)
            d = os.path.join(src, name)
            if os.path.isdir(s):
                os.makedirs(d, exist_ok=True)
                for sub in os.listdir(s):
                    os.replace(os.path.join(s, sub), os.path.join(d, sub))
            else:
                os.replace(s, d)
        shutil.rmtree(build_sub)

    def package(self):
        vi_pm = os.path.join(self.source_folder, "VI.pm")
        if os.path.isfile(vi_pm) and not os.path.exists(
                os.path.join(self.build_folder, "VI.pm")):
            shutil.copy2(vi_pm, os.path.join(self.build_folder, "VI.pm"))
        autotools = Autotools(self)
        autotools.make(target="install",
                       args=["prefix=%s" % self.package_folder,
                             "strip=/system/bin/true"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
