#!/usr/bin/env python3
"""Conan recipe — redir 3.3 (TCP port redirector CLI tool).

redir is a small TCP port redirector for UNIX: it listens on a source
port and forwards every connection to a destination address:port, running
either under inetd or as a standalone daemon.  Single-file C program
(redir.c) built with autotools; produces only the `redir` executable
(bin_PROGRAMS = redir), no library artifacts.

OHOS adaptations:
  - the upstream GitHub tarball (git archive snapshot) ships no
    `configure`, so build() must run `autoreconf -fi` to bootstrap;
  - the build host (CI sandbox / minimal OHOS image) lacks
    automake/aclocal/libtoolize (only the autoconf suite is present
    under /data/service/hnp/bin), so they are pulled in as
    tool_requires (same approach as abiword-plugin-clarisworks);
  - config.guess cannot identify HarmonyOS, so the configure triplet
    is passed explicitly (config.sub supports *-linux-ohos);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - libwrap/tcpd is optional upstream (AC_CHECK_LIB/HEADER degrade
    to no when absent) — no libwrap is published for OHOS, so the
    default `--with-libwrap=no` keeps the build dependency-free.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
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
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class RedirConan(ConanFile):
    name = "redir"
    version = "3.3"
    description = ("TCP port redirector for UNIX — listen on a source port "
                   "and forward connections to a destination address:port")
    license = "GPL-2.0-or-later"
    homepage = "https://troglobit.com/redir.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dependency-free: libwrap/tcpd is optional upstream and not
        # published for OHOS; the recipe builds with --with-libwrap=no
        pass

    def build_requirements(self):
        # The git archive ships no `configure`: build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize (only the
        # autoconf suite is present under /data/service/hnp/bin), so pull
        # them in as tool_requires (same approach as abiword-plugin-clarisworks).
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "redir is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS"),
        # so pass the triplet explicitly (config.sub supports *-linux-ohos).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # libwrap/tcpd is not published for OHOS; disable it explicitly
        tc.configure_args.append("--with-libwrap=no")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The git archive ships no `configure`: generate one from the
        # upstream configure.ac (run in source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # redir is a CLI tool, not a library — no linking info needed
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
