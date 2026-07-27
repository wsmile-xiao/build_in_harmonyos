#!/usr/bin/env python3
"""Conan recipe - abook 0.6.1 (Autotools: configure + make).

A text-based address book program for Linux/HarmonyOS.
Depends on ncurses (widechar) and readline (system-installed via cmd-pkgs).

R26: Static linking for terminal tools.
R32: settings.os must check in ("Linux", "OHOS").

All source modifications are applied via patches declared in conandata.yml:
  0001-config.guess.patch  - HarmonyOS platform recognition in config.guess (E007)
  0002-database.c.patch     - Remove inline keyword from field_id (C99 semantics)
  0003-database.h.patch     - Remove inline keyword from field_id declaration
  0004-config.sub.patch     - HarmonyOS recognition in config.sub OS list (E007)
  0005-Makefile.in.patch    - Set ACLOCAL/AUTOCONF/AUTOHEADER/AUTOMAKE to true
  0006-configure.patch      - Remove umask 077 for HMDFS compatibility
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, save, load, apply_conandata_patches,
    export_conandata_patches, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _get_prefix():
    """Get the prefix for installing/finding system dependencies.

    Always returns a user-writable path (never /usr/local).
    Uses DEFAULT_PREFIX env var (set by CI/HNP environment) or ~/usr/local.
    """
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _is_ncurses_installed(prefix):
    """Check if ncurses library is installed at prefix."""
    for libname in ["libncursesw.a", "libncurses.a"]:
        if os.path.exists(os.path.join(prefix, "lib", libname)):
            return True
    return False


def _is_ncurses_headers_installed(prefix):
    """Check if ncurses headers are installed at prefix."""
    return os.path.exists(os.path.join(prefix, "include", "curses.h"))


def _is_readline_installed(prefix):
    """Check if readline library is installed at prefix."""
    return os.path.exists(os.path.join(prefix, "lib", "libreadline.a"))


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package."""
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    cmd = f'curl -fsSL {url} | sh -s -- {name} {version} {prefix}'
    subprocess.run(cmd, shell=True, timeout=300, capture_output=True, text=True)


def _install_ncurses_headers(prefix, header_tarball):
    """Install ncurses headers from bundled tarball (cmd-pkgs only ships libs)."""
    import tarfile
    inc_dst = os.path.join(prefix, "include")
    os.makedirs(inc_dst, exist_ok=True)
    if header_tarball and os.path.exists(header_tarball):
        with tarfile.open(header_tarball, "r:gz") as tar:
            tar.extractall(inc_dst)


class AbookConan(ConanFile):
    name = "abook"
    version = "0.6.1"
    description = "A text-based address book program"
    license = "MIT"
    homepage = "https://abook.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ncurses-headers.tar.gz", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # ncurses and readline are system-installed via cmd-pkgs, not conan deps.
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "abook is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply all patches declared in conandata.yml (R3: patches via conandata)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()
        hdr_tarball = os.path.join(self.source_folder, "ncurses-headers.tar.gz")

        # Ensure system dependencies (ncurses, readline) are installed via cmd-pkgs
        if not _is_ncurses_installed(prefix):
            _install_cmd_pkg("ncurses", "6.4", prefix)
        # cmd-pkgs ncurses only ships library, not headers - install from bundled tarball
        if not _is_ncurses_headers_installed(prefix):
            _install_ncurses_headers(prefix, hdr_tarball)
        if not _is_readline_installed(prefix):
            _install_cmd_pkg("readline", "8.2", prefix)

        tc = AutotoolsToolchain(self)
        # R26: Terminal tools - system same-name libs must be static
        tc.extra_ldflags.append("-static")
        # System-installed ncurses and readline (via cmd-pkgs)
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib")
        if os.path.isdir(inc):
            tc.extra_cflags.append("-I" + inc)
        if os.path.isdir(lib):
            tc.extra_ldflags.append("-L" + lib)
        # Tell configure where ncurses is installed
        tc.configure_args.append("--with-curses=" + prefix)
        tc.generate()

    def _fix_config_status(self, build):
        """Fix config.status: remove umask 077 for temp dir (HMDFS permission).

        config.status is a generated file (not in source tarball), so it
        cannot be patched via conandata.yml. This fix must be applied inline
        after configure generates it.
        """
        path = os.path.join(build, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # Fix config.status (generated file - cannot be a source patch)
        self._fix_config_status(self.build_folder)
        # If config.status failed during configure, re-run it manually
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self._fix_config_status(self.build_folder)
            self.run("cd " + self.build_folder + " && bash config.status")
        # Build
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # abook is a standalone terminal binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure abook binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
