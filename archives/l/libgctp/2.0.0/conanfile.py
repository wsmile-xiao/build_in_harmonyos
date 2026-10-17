#!/usr/bin/env python3
"""Conan recipe — libgctp 2.0.0.

USGS GCTPC: General Cartographic Transformation Package (map projection
library, pure C).  Upstream GitHub tag v2.0.0.

OHOS adaptations:
  patches (conandata.yml, modified-file diffs only):
    0001-drop-fortran-spload.patch - remove AC_PROG_F77 and the Fortran
        helper program spload (a noinst data-conversion utility for SPCS
        parameter files).  The library itself is pure C; the OHOS toolchain
        ships no Fortran compiler and configure aborts when AC_PROG_F77
        finds none.  The upstream test suite (30 automake check scripts)
        reads its inputs from test/proj and does not depend on spload
        output, so the trim does not reduce test coverage.
  - the tarball is a 1998-era autotools snapshot: build() runs
    `autoreconf -fi` (with automake/libtool tool_requires) to regenerate
    configure and modern config.guess/config.sub (the originals cannot
    identify the HarmonyOS host);
  - the generated configure is patched to drop `umask 077` from the
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir
    into an unwritable drwx--S--- dir);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - `make check` runs the 30 upstream test scripts (L1 upstream tests).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir.  Tolerates absence (autoconf version drift)."""
    old_tmp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
    new_tmp = 'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`'
    old_mkdir = '(umask 077 && mkdir "$tmp")'
    new_mkdir = 'mkdir "$tmp"'
    try:
        replace_in_file(conanfile, path, old_tmp, new_tmp)
        replace_in_file(conanfile, path, old_mkdir, new_mkdir)
    except Exception:
        # pattern absent (older/newer autoconf wording) — nothing to fix
        pass


class LibgctpConan(ConanFile):
    name = "libgctp"
    version = "2.0.0"
    description = ("USGS GCTPC - General Cartographic Transformation Package: "
                   "C library converting coordinates between map projections")
    license = "Public Domain"
    homepage = "https://github.com/OkoSanto/GCTP"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 1998-era snapshot: configure/config.guess/config.sub must be
        # regenerated (autoreconf -fi) before configuring.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgctp is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # The regenerated config.guess cannot identify HarmonyOS (uname -s =
        # "HarmonyOS"); pass both triplets explicitly so configure never runs
        # the config.guess probe (same approach as abiword-plugin-*).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # E386 family: the ohos-aarch64 profile [buildenv] exports
        # CONFIG_SHELL=/data/service/hnp/bin/bash, whose getcwd() fails on
        # HMDFS paths; autoconf re-execs itself via CONFIG_SHELL, so
        # configure dies with "working directory cannot be determined".
        # Inline env prefixes are the only reliable override (toolchain env
        # is sourced before profile buildenv in conanbuild.sh).
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi",
                 cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        # E490: adaptation paths may strip exec bits from autotools helpers
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "compile", "depcomp",
                       "test-driver"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        # Configure/make with the shell routed away from the hnp bash.
        # configure runs VPATH from the build folder; CC/CFLAGS/LDFLAGS come
        # from the AutotoolsToolchain via the conanbuild environment.
        configure_cmd = (
            "env -u CONFIG_SHELL SHELL=/bin/sh sh "
            + shlex.quote(os.path.join(self.source_folder, "configure"))
            + " --build=aarch64-unknown-linux-ohos"
            + " --host=aarch64-unknown-linux-ohos"
            + " --enable-static --disable-shared"
            + " --prefix=" + shlex.quote(self.package_folder)
        )
        self.run(configure_cmd, cwd=self.build_folder, env="conanbuild")
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh make -j1",
                 cwd=self.build_folder, env="conanbuild")
        # L1: run the upstream test suite (30 automake check scripts driving
        # the testproj binary against bundled validation data)
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh make -j1 check",
                 cwd=self.build_folder, env="conanbuild")

    def package(self):
        # Conan's Autotools.install() runs `make install DESTDIR=<pkg>` which,
        # combined with the absolute --prefix, nests the whole prefix path
        # inside the package folder.  Install without DESTDIR so the absolute
        # prefix (= package folder) lands directly.
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh make -j1 install",
                 cwd=self.build_folder, env="conanbuild")

    def package_info(self):
        # The installed static archive is libgctp.a (libtool's -release
        # 2.0.0 renames only the shared object, not the static archive).
        self.cpp_info.libs = ["gctp"]
