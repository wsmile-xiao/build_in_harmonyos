#!/usr/bin/env python3
"""Conan recipe — owamp 3.4-10.

One-Way Active Measurement Protocol (OWAMP) client/server toolkit from
Internet2 — measures one-way latency between hosts (RFC 4656).
Builds owampd (server), owping (client) + owstats/owfetch/owup symlinks,
powstream (continuous-test daemon) and the owtvec validation program.

The upstream tarball ships a 2014-era `configure` whose config.sub (2009)
does not recognize aarch64-unknown-linux-ohos, so build() regenerates the
autotools files with `autoreconf -fi` (modern automake/autoconf from
tool_requires, same approach as abiword-plugin-clarisworks).  The upstream
configure.ac hard-requires the I2util library (AC_SEARCH_LIBS
[I2AddrByNode] + AC_CHECK_HEADERS I2util/util.h I2util/conf.h), which is
satisfied by the published i2util/1.2 package.

OHOS adaptations:
  patches (conandata.yml, modified-file diff only):
    0001-configure.ac.patch - modernize AM_INIT_AUTOMAKE([foreign]) +
      AC_CONFIG_HEADERS + AC_CONFIG_MACRO_DIR([config]) so automake 1.18 /
      autoconf 2.7x accept the file and aclocal finds config/c-attribute.m4
      (I2_C___ATTRIBUTE__).
  build notes:
    - `autoreconf -fi` regenerates configure/config.sub (E114 umask 077 in
      the generated configure is dropped at runtime);
    - configure runs with --build/--host=aarch64-unknown-linux-ohos
      (config.guess cannot identify HarmonyOS) and the i2util package
      include/lib dirs added to CFLAGS/LDFLAGS;
    - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
    - upstream test entry is the owtvec binary (test/owtvec.c validates
      AES-based Exponential Deviates from OWAMP spec Appendix B); it is a
      bin_PROGRAMS, not a TESTS target, so `make check` is empty — the test
      is executed explicitly in build() and reported separately.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
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


class OwampConan(ConanFile):
    name = "owamp"
    version = "3.4-10"
    description = "One-Way Active Measurement Protocol (OWAMP) client/server toolkit (RFC 4656)"
    license = "Apache-2.0"
    homepage = "https://software.internet2.edu/owamp/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # upstream configure.ac hard-requires I2util (I2AddrByNode + headers)
        self.requires("i2util/1.2")

    def build_requirements(self):
        # The shipped config.sub (2009) does not know the OHOS triplet, so
        # build() must run `autoreconf -fi` to regenerate configure with the
        # modern automake/autoconf config.sub (same approach as
        # abiword-plugin-clarisworks / argp-standalone).
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "owamp is only supported on Linux/OHOS, not " +
                str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # export the conandata.yml declared patches (0001-configure.ac.patch)
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly
        # (config.sub regenerated by autoreconf supports *-linux-ohos)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # feed the i2util package include/lib dirs into the build so
        # AC_SEARCH_LIBS(I2AddrByNode) and AC_CHECK_HEADERS(I2util/*.h)
        # succeed in configure (cpp_info paths are relative to package_folder)
        dep = self.dependencies["i2util"]
        for inc in dep.cpp_info.includedirs:
            inc_abs = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
            tc.extra_cflags.append("-I" + inc_abs)
        for libdir in dep.cpp_info.libdirs:
            lib_abs = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
            tc.extra_ldflags.append("-L" + lib_abs)
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # Regenerate configure with a config.sub that knows the OHOS triplet.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Upstream test entry: owtvec (bin_PROGRAMS, not a TESTS target, so
        # `make check` is empty).  Run it explicitly as the upstream test.
        owtvec = os.path.join(self.build_folder, "test", "owtvec")
        if os.path.exists(owtvec):
            self.run(owtvec, cwd=self.build_folder, env="conanrun")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # owamp ships CLI tools (owampd/owping/owstats/owfetch/owup/powstream/owtvec)
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
