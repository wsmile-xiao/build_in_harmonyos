#!/usr/bin/env python3
"""Conan recipe - screen 5.0.0 (Autotools: configure + make).

Terminal multiplexer for managing multiple terminal sessions.
Depends on ncurses (widechar), system-installed via cmd-pkgs.

R26: Static linking for system-name libraries.
R32: settings.os must check in ("Linux", "OHOS").
R38: screen is a command-line tool (commands.json required).

All source modifications are applied via patches declared in conandata.yml:
  0001-configure.patch             - configure umask 077→022 (HMDFS) + getspnam detection
  0002-misc.c.patch                 - poll() replaced with POSIX close() loop
  0003-socket.c.patch              - socket.c seteuid/setegid graceful failure + HAVE_GETSPNAM
  0004-tests-macros.h.patch         - Test macros.h compilation fix
  0005-tests-mallocmock.c.patch     - Test mallocmock.c compilation fix
  0006-tests-test-winmsgbuf.c.patch - Test winmsgbuf compilation fix
  0007-tests-test-winmsgcond.c.patch - Test winmsgcond compilation fix
"""
import os
import shutil
import subprocess
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, save, load, apply_conandata_patches,
    export_conandata_patches,
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


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package."""
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    # Use Python standard library for download (CI L0o: no external network commands)
    try:
        with urllib.request.urlopen(url, timeout=300) as resp:
            script_content = resp.read().decode("utf-8")
    except Exception as e:
        raise ConanInvalidConfiguration(
            f"Failed to download cmd-pkgs install script: {e}"
        )
    # OHOS: subprocess posix_spawn does not search PATH for bare names.
    sh_path = shutil.which("sh") or "/system/bin/sh"
    if not os.path.exists(sh_path):
        sh_path = "/bin/sh"
    result = subprocess.run(
        [sh_path, "-s", "--", name, version, prefix],
        input=script_content, timeout=300, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ConanInvalidConfiguration(
            f"Failed to install {name} {version} via cmd-pkgs: "
            f"rc={result.returncode} stderr={result.stderr.strip()}"
        )


class ScreenConan(ConanFile):
    name = "screen"
    version = "5.0.0"
    package_type = "application"
    description = "Terminal multiplexer for managing multiple terminal sessions"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/screen/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses is system-installed via cmd-pkgs, not a conan dep.
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "screen is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply all patches declared in conandata.yml (R3: patches via conandata)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()

        # Ensure system dependency (ncurses) is installed via cmd-pkgs
        if not _is_ncurses_installed(prefix):
            _install_cmd_pkg("ncurses", "6.4", prefix)

        tc = AutotoolsToolchain(self)
        # R26: System-name libs must be static
        tc.extra_ldflags.append("-static")
        # System-installed ncurses (via cmd-pkgs)
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib")
        if os.path.isdir(inc):
            tc.extra_cflags.append("-I" + inc)
        if os.path.isdir(lib):
            tc.extra_ldflags.append("-L" + lib)
        # Add source directory to include path (screen generates comm.h in
        # build dir but includes headers from source dir like acls.h)
        tc.extra_cflags.append("-I" + self.source_folder)
        # OHOS has no PAM
        tc.configure_args.append("--disable-pam")
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
            self.run(f'cd "{self.build_folder}" && bash config.status')
        # Build
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # screen is a standalone terminal binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure screen binary is on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
