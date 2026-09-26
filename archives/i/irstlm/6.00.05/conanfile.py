#!/usr/bin/env python3
"""Conan recipe — irstlm 6.00.05.

IRSTLM: IRST Language Model Toolkit (n-gram language modeling for speech
recognition / statistical MT).  Builds the libirstlm static library plus
the dict/ngt/compile-lm/score-lm/... command-line tools for HarmonyOS PC.

OHOS adaptations:
  - the GitHub tag tarball ships no `configure` (autotools-generated files
    are not versioned), so build() bootstraps it with `autoreconf -fi`;
  - config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS", kernel
    "HongMeng Kernel"), so the triplet is passed explicitly
    (config.sub accepts *-linux-ohos) to skip the probe;
  - the generated configure is patched to drop `umask 077` from the
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir into
    an unwritable drwx--S--- dir);
  - the cxx0 dialect flag `-std=c++0x` is moved from CPPFLAGS to CXXFLAGS
    (patch 0001) so C sources (cmd.c/thpool.c) are not compiled with a
    C++-only flag;
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
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


class IrstlmConan(ConanFile):
    name = "irstlm"
    version = "6.00.05"
    description = "IRSTLM: IRST Language Model Toolkit"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/irstlm-team/irstlm"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac links -lz unconditionally (mfstream.cpp uses gzopen/
        # gzread/gzclose via gzfilebuf.h)
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # The git archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize (only the
        # autoconf suite is present under /data/service/hnp/bin), so pull
        # them in as tool_requires (same approach as abiword-plugin-*).
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "irstlm is only supported on Linux/OHOS, not " +
                str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel"); pass the triplet explicitly
        # (config.sub accepts *-linux-ohos) so configure never runs the
        # config.guess probe; same approach as abiword-plugin-clarisworks.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # upstream docs: --disable-doc skips latex documentation
        tc.configure_args.append("--disable-doc")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The git archive ships no `configure`: generate one from
        # configure.ac (run in source folder).
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
        self.cpp_info.libs = ["irstlm"]
