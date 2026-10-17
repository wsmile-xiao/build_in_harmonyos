#!/usr/bin/env python3
"""Conan recipe — cbootimage (NVIDIA Tegra BCT image compiler tool).

cbootimage is a standalone CLI tool that compiles BCT (Boot Configuration
Table) images for Tegra-based devices; builds two executables (cbootimage,
bct_dump) and no shared/static libraries.

Build notes (git snapshot, no released tarball):
  - the git archive ships no `configure`, so build() runs `autoreconf -fi`;
  - the generated configure is then patched to drop `umask 077` from the
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir into
    an unwritable drwx--S--- dir);
  - the --build/--host triplet is passed explicitly (E490: config.guess
    cannot identify HarmonyOS, same approach as argp-standalone /
    abiword-plugin-clarisworks);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
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


class CbootimageConan(ConanFile):
    name = "cbootimage"
    version = "1.8-git20190919.80c499e"
    description = "Tool to generate, update and dump BCT images for NVIDIA Tegra devices"
    license = "GPL-2.0"
    homepage = "https://github.com/NVIDIA/cbootimage"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The git archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize (only the
        # autoconf suite is present under /data/service/hnp/bin), so pull
        # them in as tool_requires (same approach as argp-standalone /
        # abiword-plugin-clarisworks).  tool_requires are resolved with the
        # *build* profile, so both -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # E490: config.guess cannot identify HarmonyOS (uname -s =
        # "HarmonyOS"), pass the triplet explicitly (config.sub supports
        # *-linux-ohos); cbootimage's configure.ac accepts it.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # The git archive ships no `configure`: generate one from the
        # upstream configure.ac (run in source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        for fn in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                _drop_umask_077(self, p)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # cbootimage is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]