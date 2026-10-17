#!/usr/bin/env python3
"""Conan recipe for gnu-typist 2.10.1."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnutypistConan(ConanFile):
    name = "gnu-typist"
    version = "2.10.1"
    description = "GNU Typist, a typing tutor"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gtypist/"
    url = ""

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def _compat_include_dir(self):
        return os.path.join(self.build_folder, "_compat_include")

    def _ncurses_flags(self):
        ncurses = self.dependencies["ncurses"].cpp_info
        include_dirs = [self._compat_include_dir()] + list(ncurses.includedirs)
        cflags = " ".join(f"-I{path}" for path in include_dirs)
        ldflags = " ".join(f"-L{path}" for path in ncurses.libdirs)
        return cflags, ldflags

    def _configure_args(self):
        args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ]
        if self.settings.os == "OHOS":
            args.extend(["--build=aarch64-linux-gnu", "--host=aarch64-linux-gnu"])
        args.append("--disable-nls")
        ncurses_cflags, ncurses_ldflags = self._ncurses_flags()
        if ncurses_cflags:
            args.append("CPPFLAGS=" + ncurses_cflags)
        if ncurses_ldflags:
            args.append("LDFLAGS=" + ncurses_ldflags)
        return args

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        # Suppress int-conversion error from bundled getopt.c (uses 0 as NULL)
        tc.extra_cflags.append("-Wno-int-conversion")
        # Define gettext stubs for NLS-disabled builds (via -include to avoid
        # shell quoting issues with parentheses in -D flags)
        tc.extra_cflags.append("-include")
        tc.extra_cflags.append("_tools/gettext_stub.h")
        ncurses_cflags, ncurses_ldflags = self._ncurses_flags()
        if ncurses_cflags:
            tc.extra_cflags.append(ncurses_cflags)
        if ncurses_ldflags:
            tc.extra_ldflags.append(ncurses_ldflags)
        tc.generate()

    def build(self):
        import os as _os
        # Save full environment to restore after build (R33)
        _saved_environ = dict(_os.environ)
        try:
            # Inline mktemp fix for HMDFS: upstream configure uses mktemp -d
            # which fails on HMDFS (t=$(mktemp -p . confXXXXXX.tmp) fallback)
            from pathlib import Path as _Path
            _cf = _Path(self.source_folder) / "configure"
            if _cf.is_file():
                _txt = _cf.read_text(encoding="utf-8")
                _old = '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
                _new = '  tmp=`(umask 077 && t=$(mktemp -p . confXXXXXX.tmp) && rm -f "$t" && mkdir -p "$t" && echo "$t") 2>/dev/null` &&'
                if _old in _txt:
                    _cf.write_text(_txt.replace(_old, _new), encoding="utf-8")
                _cf.chmod(_cf.stat().st_mode | 0o755)
            compat_ncursesw = _Path(self._compat_include_dir()) / "ncursesw"
            compat_ncursesw.mkdir(parents=True, exist_ok=True)
            for header in ("ncurses.h", "curses.h", "term.h", "unctrl.h"):
                (compat_ncursesw / header).write_text(
                    f"#include <{header}>\n", encoding="utf-8"
                )
            # [R33] PATH adjustments for OHOS platform limitations (E106/E079):
            #   - Prefix /bin: HMDFS GNU cat stdout permission issue (E106)
            #   - _tools/: help2man/makeinfo not available on OHOS (E079)
            _os.environ["PATH"] = "/bin:" + _saved_environ.get("PATH", "")
            config_shell = _os.environ.get("CONFIG_SHELL")
            if not config_shell or not _os.path.exists(config_shell):
                config_shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
            # Create wrapper scripts for missing tools
            _os.makedirs("_tools", exist_ok=True)
            with open("_tools/help2man", "w") as f:
                f.write(f"#!{config_shell}\nexit 0\n")
            _os.chmod("_tools/help2man", 0o755)
            with open("_tools/makeinfo", "w") as f:
                f.write(f"#!{config_shell}\nexit 0\n")
            _os.chmod("_tools/makeinfo", 0o755)
            with open("_tools/gettext_stub.h", "w") as f:
                f.write("/* gettext stub for NLS-disabled builds */\n")
                f.write("#define gettext(x) (x)\n")
                f.write("#define _(x) (x)\n")
            _os.environ["PATH"] = _os.path.abspath("_tools") + ":" + _os.environ.get("PATH", "")
            configure_env = {
                "CONFIG_SHELL": config_shell,
                "SHELL": config_shell,
                "LD": shutil.which("ld.lld") or shutil.which("ld") or "ld",
                "AR": shutil.which("llvm-ar") or shutil.which("ar") or "ar",
                "RANLIB": shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib",
            }
            configure_cmd = "{0} {1} {2} {3}".format(
                " ".join(f"{key}={shlex.quote(value)}" for key, value in configure_env.items()),
                shlex.quote(config_shell),
                shlex.quote(str(_cf)),
                shlex.join(self._configure_args()),
            )
            self.run(configure_cmd, cwd=self.build_folder, env="conanbuild")
            autotools = Autotools(self)
            autotools.make(args=["-j1"])
        finally:
            # R33: restore original environment after build
            _os.environ.clear()
            _os.environ.update(_saved_environ)

    def package(self):
        import os as _os
        _saved_path = _os.environ.get("PATH", "")
        try:
            # _tools/ created in build() remains on disk; add to PATH for install.
            _tools_dir = _os.path.join(self.build_folder, "_tools")
            if _os.path.isdir(_tools_dir):
                _os.environ["PATH"] = _tools_dir + ":" + _saved_path
            autotools = Autotools(self)
            autotools.install()
            copy(self, "COPYING", src=self.source_folder,
                 dst=_os.path.join(self.package_folder, "licenses"),
                 keep_path=False)
        finally:
            _os.environ["PATH"] = _saved_path

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bin_dir = os.path.join(self.package_folder, "bin")
        self.runenv_info.append_path("PATH", bin_dir)
        self.buildenv_info.append_path("PATH", bin_dir)
