#!/usr/bin/env python3
"""Conan recipe — aamath 0.3.1 (Makefile).

aamath renders mathematical expressions as ASCII art text.
Build system: plain Makefile (no configure script).
Depends on readline + ncurses (system pre-built libraries).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


def _get_prefix():
    """Get the prefix for system dependencies (DEFAULT_PREFIX or ~/usr/local)."""
    return os.environ.get("DEFAULT_PREFIX",
                          os.path.join(os.path.expanduser("~"), "usr", "local"))


def _is_readline_installed(prefix):
    """Check if readline library is installed at prefix."""
    return os.path.exists(os.path.join(prefix, "lib", "libreadline.a"))


def _is_ncurses_installed(prefix):
    """Check if ncurses library is installed at prefix."""
    for libname in ("libncursesw.a", "libncurses.a"):
        if os.path.exists(os.path.join(prefix, "lib", libname)):
            return True
    return False


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package."""
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    cmd = f'curl -fsSL {url} | sh -s -- {name} {version} {prefix}'
    subprocess.run(cmd, shell=True, timeout=300, capture_output=True, text=True)


class AamathConan(ConanFile):
    name = "aamath"
    version = "0.3.1"
    description = "Render mathematical expressions as ASCII art text"
    license = "GPL-2.0-or-later"
    homepage = "https://cdn.netbsd.org/pub/pkgsrc/distfiles/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aamath supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_readline_headers(self, sysroot):
        """Ensure readline dev headers exist; extract from source if missing."""
        rl_header = os.path.join(sysroot, "include", "readline", "readline.h")
        if os.path.isfile(rl_header):
            return
        # cmd-pkgs installs runtime .so only; extract dev headers from source
        # Use conan.tools.files.get() — handles CI mirror URL lists natively
        rl_src = self.conan_data.get("readline_source", {})
        tmpdir = os.path.join(self.build_folder, "_rl_headers")
        get(self, url=rl_src["url"], sha256=rl_src.get("sha256"),
            destination=tmpdir, strip_root=True)
        self.run(
            f"mkdir -p {sysroot}/include/readline && "
            f"cp {tmpdir}/*.h {sysroot}/include/readline/",
            env="conanbuild",
        )

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cxx = comp.get("cpp", "clang++") if comp else "clang++"

        sysroot = _get_prefix()

        # Ensure system libraries are installed via cmd-pkgs (CI worker doesn't pre-install)
        if not _is_readline_installed(sysroot):
            _install_cmd_pkg("readline", "8.2", sysroot)
        if not _is_ncurses_installed(sysroot):
            _install_cmd_pkg("ncurses", "6.4", sysroot)

        self._ensure_readline_headers(sysroot)

        # cmd-pkgs may install libncursesw.a (widechar) instead of libncurses.a
        ncurses_lib = "ncursesw" if os.path.exists(
            os.path.join(sysroot, "lib", "libncursesw.a")) else "ncurses"

        src = self.source_folder

        self.run(
            f"make -f Makefile.good -j1 "
            f"CXX='{cxx}' "
            f"LD='{cxx}' "
            f"CXXFLAGS='-Wall -O2 -fPIC -DUSE_READLINE -I{sysroot}/include' "
            f"LFLAGS='-L{sysroot}/lib' "
            f"LIBS='-lreadline -l{ncurses_lib}'",
            env="conanbuild",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        self.run(
            f"make -f Makefile.good install "
            f"PREFIX=/ DESTDIR={self.package_folder}",
            env="conanbuild",
            cwd=src,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["readline", "ncurses"]
