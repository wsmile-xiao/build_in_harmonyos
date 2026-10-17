#!/usr/bin/env python3
"""Conan recipe - libcdk5 5.0.20260119 (Autotools: configure + make).

libcdk5 (CDK, Curses Development Kit) is a C library providing predefined curses
widgets (buttons, menus, scrolllists, dialogs, calendars, etc.) for terminal
apps. 上游库名为 cdk，本仓 Conan 包名/归档键名为 libcdk5（对应第 5 代主线）。

Depends on ncurses (widechar) installed via cmd-pkgs (system-installed, not a
conan dependency). cmd-pkgs ships the runtime library only, headers must be
retrieved from the upstream source tarball.

R26: Static linking for system-name libraries (ncurses).
R32: settings.os must check in ("Linux", "OHOS").
R33: build() does not depend on undefined shell env vars; compiler/flags come
     from Conan AutotoolsToolchain.

All source modifications are applied via patches declared in conandata.yml:
  0001-config.guess.patch  - HarmonyOS platform recognition in config.guess (E007)
  0002-config.sub.patch   - HarmonyOS recognition in config.sub OS list (E007)
  0003-configure.patch    - Remove umask 077 from configure temp dir (HMDFS fix)
"""
import os
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches,
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
    """Check if ncurses widechar library is installed at prefix."""
    for libname in ["libncursesw.a", "libncurses.a"]:
        if os.path.exists(os.path.join(prefix, "lib", libname)):
            return True
    return False


def _is_ncurses_headers_installed(prefix):
    """Check if ncurses headers are installed at prefix."""
    return os.path.exists(os.path.join(prefix, "include", "curses.h"))


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package."""
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    cmd = f'curl -fsSL {url} | sh -s -- {name} {version} {prefix}'
    result = subprocess.run(cmd, shell=True, timeout=300, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"cmd-pkgs {name}/{version} install failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _install_ncurses_headers(prefix, source_folder):
    """Install ncurses headers from the bundled upstream ncurses source.

    cmd-pkgs ncurses only ships the runtime library, not development headers.
    CDK's configure needs curses.h, so we extract the ncurses headers from the
    upstream ncurses 6.4 source tarball into the prefix include directory.
    """
    inc_dst = os.path.join(prefix, "include")
    os.makedirs(inc_dst, exist_ok=True)
    # Look for an ncurses-headers tarball shipped alongside the recipe
    hdr_tarball = os.path.join(source_folder, "ncurses-headers.tar.gz")
    if not os.path.exists(hdr_tarball):
        raise FileNotFoundError(
            f"ncurses-headers.tar.gz not found at {hdr_tarball}; cmd-pkgs ncurses ships the "
            "runtime library only, configure needs curses.h — vendor the headers tarball "
            "in the recipe folder and ensure export_sources() + .gitignore lets it ship."
        )
    with tarfile.open(hdr_tarball, "r:gz") as tar:
        tar.extractall(inc_dst)


class Libcdk5Conan(ConanFile):
    name = "libcdk5"
    version = "5.0.20260119"
    description = "Curses Development Kit - predefined curses widgets for terminal apps"
    license = "MIT"
    homepage = "https://invisible-island.net/cdk"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ncurses-headers.tar.gz", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # ncurses is system-installed via cmd-pkgs, not a conan dependency.
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcdk5 is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply all patches declared in conandata.yml (R3: patches via conandata)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()

        # Ensure system dependency ncurses (widechar) is installed via cmd-pkgs
        if not _is_ncurses_installed(prefix):
            _install_cmd_pkg("ncurses", "6.4", prefix)
        # cmd-pkgs ncurses only ships the library, not headers - install from bundled tarball
        if not _is_ncurses_headers_installed(prefix):
            _install_ncurses_headers(prefix, self.source_folder)

        # HMDFS: configure/config.status cannot create a writable tmp dir via
        # mktemp or mkdir (umask 077 + chmod unsupported), and the runner-injected
        # $TMPDIR is not writable by config.status. Patch 0003 points tmp at the
        # fixed relative path ./.hmbs_tmp; pre-create it here via Python os.makedirs
        # (bypassing shell mkdir limits) so config.status's sed/cat succeed.
        hmbs_tmp = os.path.join(self.build_folder, ".hmbs_tmp")
        os.makedirs(hmbs_tmp, exist_ok=True)

        tc = AutotoolsToolchain(self)
        # R26: System-name libs default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # System-installed ncurses (via cmd-pkgs) - point configure at it.
        # configure's CF_WITH_CURSES_DIR auto-adds -I$prefix/include to CPPFLAGS
        # for header search (CF_CURSES_HEADER uses #include <curses.h>, which
        # reads CPPFLAGS, not CFLAGS). Do NOT inject -I via extra_cflags: that
        # would land in CFLAGS and configure warns "uses CFLAGS to hold
        # CPPFLAGS options" (seen in round 8 log).
        # However CF_WITH_CURSES_DIR's CF_ADD_LIBDIR($prefix/lib) only injects
        # -L into configure-internal LDFLAGS, not into the Conan build env that
        # AC_LINK_IFELSE uses for the tgoto/initscr library probes. abook (same
        # cmd-pkgs ncurses 6.4) empirically must inject -L via extra_ldflags.
        lib = os.path.join(prefix, "lib")
        if os.path.isdir(lib):
            tc.extra_ldflags.append("-L" + lib)
        # cmd-pkgs ncurses 6.4 ships libncursesw.a (widechar). CDK's configure
        # defaults cf_cv_screen=curses which probes -lcurses (round 9-10 logs:
        # "checking for specified curses library type... curses" then all
        # "-lncurses/curses/..." probes return no). Must explicitly select the
        # ncursesw variant so CF_NCURSES_CONFIG(ncursesw) probes -lncursesw and
        # configure.in's case sets LIB_ROOTNAME=cdkw (matches cpp_info.libs).
        tc.configure_args.append("--with-ncursesw")
        tc.configure_args.append("--with-curses-dir=" + prefix)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS: out-of-tree build puts generated subdirectory outputs (include/,
        # man/, cli/, examples/, demos/) in builddir cwd, but HMDFS shell mkdir
        # cannot create writable subdirs and getcwd() fails so relative subdir
        # paths cannot be resolved. Upstream Makefile.in writes GEN_SCALE/SLIDER
        # outputs via relative paths (e.g. >include/dscale.h) assuming srcdir==
        # builddir. Pre-create the make-stage write-target subdirs here via Python
        # os.makedirs (bypassing shell mkdir limits) so the relative redirections
        # succeed. Subdirs in srcdir already exist (source tarball); only builddir
        # needs them. Patches config.status via ac_out for the same reason.
        # NOTE: cdk-config is a configure-generated root file, NOT a subdir —
        # exclude it (os.makedirs on an existing file raises FileExistsError).
        for sub in ("include", "man", "cli", "examples", "demos"):
            sub_path = os.path.join(self.build_folder, sub)
            if os.path.isdir(sub_path) or not os.path.exists(sub_path):
                os.makedirs(sub_path, exist_ok=True)
        # Build
        autotools.make(args=["-j1"])
        # Upstream `check` target: CDK's top-level Makefile.in defines a `check`
        # target that prints "This interactive program has no automated tests" and
        # exits 0 (audited). HMBS requires upstream test entry points to be executed
        # on the real machine even when they declare no automated tests — `no_tests`
        # status is rejected when the `check` target exists. Run `make check` directly
        # via Python subprocess (NOT autotools.make — its capture/exception semantics
        # on CDK's echo-only check target mislead the pass/fail verdict) to get the
        # real exit code + output. Write a structured result (first line __PASSED__ or
        # __FAILED__) + captured output to a file installed into the package so
        # test_package can emit HMBS_UPSTREAM_TEST_RESULT with real execution data.
        # Success = exit code 0 (the check target ran to completion); CDK's check has
        # no assertions to fail.
        check_log = os.path.join(self.build_folder, "upstream_check.log")
        make_bin = os.environ.get("HMBS_MAKE") or "make"
        try:
            proc = subprocess.run(
                [make_bin, "check"],
                cwd=self.build_folder,
                capture_output=True, text=True,
                env=os.environ.copy(),
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = (proc.returncode == 0)
        except Exception as exc:
            out = "subprocess failed: " + str(exc)
            ok = False
        with open(check_log, "w", encoding="utf-8") as fh:
            fh.write(("__PASSED__\n" if ok else "__FAILED__\n") + (out if out else "(empty output)"))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Install the upstream `make check` execution log so test_package can read it
        # and emit HMBS_UPSTREAM_TEST_RESULT with real execution data (HMBS rejects
        # no_tests when the `check` target exists; the log proves it ran on the real machine).
        check_log = os.path.join(self.build_folder, "upstream_check.log")
        if os.path.exists(check_log):
            copy(self, "upstream_check.log", self.build_folder, self.package_folder)

    def package_info(self):
        # CDK library name depends on the curses variant selected by configure:
        #   ncurses  -> cdk    (default)
        #   ncursesw -> cdkw   (widechar, used here via --with-curses-dir pointing at ncursesw)
        # The widechar build is what cmd-pkgs ncurses 6.4 provides, so libcdkw.a is produced.
        self.cpp_info.libs = ["cdkw"]
        # cdk5-config helper script is installed to bin/
        self.cpp_info.bindirs = ["bin"]
