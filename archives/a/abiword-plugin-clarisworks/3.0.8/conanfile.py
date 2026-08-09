#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-clarisworks 3.0.8.

Builds the AbiWord ClarisWorks/AppleWorks 5 (.cwk) import plugin module for
HarmonyOS PC.  The upstream tarball is the full AbiWord 3.0.8 source; only
the self-contained clarisworks plugin is built (minimal configure.ac +
Makefile.am, mirroring the sibling abiword-plugin-bmp adaptation).

The AbiWord runtime API (IE_Imp / PD_Document / XAP_Module / UT_GrowBuf ...)
and the libgsf GsfInput API used by the plugin are provided by a compile-time
compat shim (exported via export_sources).  libgsf / AbiWord core are NOT
published for OHOS, so the shim keeps the module dependency-free.

OHOS adaptations:
  patches (conandata.yml, modified-file diffs only):
    0001-Makefile.am.patch   - replace full AbiWord Makefile.am with a minimal
                              plugin build (configure.ac 也一并最小化)
    0002-configure.ac.patch  - replace full AbiWord configure.ac with a minimal one
  export_sources (no new-file patches — toybox `patch --dry-run` on OHOS
  applies new-file patches for real, polluting the pristine orig dir and
  breaking the patch pipeline; modified-file diffs are safe):
    compat/  - AbiWord runtime + libgsf GsfInput compile-time shim
    tests/   - tests/test_clarisworks_plugin.cpp (end-to-end, R34)

Build notes:
  - the git archive ships no `configure`, so build() runs `autoreconf -fi`;
  - the generated configure is then patched to drop `umask 077` from the
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir into
    an unwritable drwx--S--- dir);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - `make check` runs the end-to-end plugin test (L1 upstream test).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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


class AbiwordPluginClarisworksConan(ConanFile):
    name = "abiword-plugin-clarisworks"
    version = "3.0.8"
    description = "AbiWord ClarisWorks/AppleWorks 5 (.cwk) import plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://www.abisource.com/"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # compat/ (AbiWord + libgsf shim) and tests/ are source files, not
        # patches: toybox patch --dry-run on OHOS applies new-file patches for
        # real (pollutes orig dir and breaks the patch pipeline).  Exporting
        # them keeps the patch set limited to modified-file diffs (Makefile.am,
        # configure.ac).  Pattern "*" copies the directory contents, keeping
        # the relative paths (compat/, tests/).
        copy(self, "*", src=os.path.join(self.recipe_folder, "compat"),
             dst=os.path.join(self.export_sources_folder, "compat"))
        copy(self, "*", src=os.path.join(self.recipe_folder, "tests"),
             dst=os.path.join(self.export_sources_folder, "tests"))

    def requirements(self):
        # dependency-free: AbiWord core / libgsf APIs are provided by the
        # compat shim embedded in the module
        pass

    def build_requirements(self):
        # The git archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize (only the
        # autoconf suite is present under /data/service/hnp/bin), so pull
        # them in as tool_requires (same approach as argp-standalone).
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "abiword-plugin-clarisworks is only supported on Linux/OHOS, "
                "not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        # export sources (patches/, compat/, tests/) are auto-merged into the
        # source folder by conan before source() runs, so compat/ and tests/
        # are already present here.
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel") and its compiler probe also fails under
        # the HMDFS tmp dir (E114-style permission issue).  Pass the triplet
        # explicitly (config.sub supports *-linux-ohos) so configure never
        # runs the config.guess probe; same approach as argp-standalone.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The git archive ships no `configure`: generate one from the
        # minimal configure.ac applied by the patches (run in source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # L1: run the upstream end-to-end plugin test
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # dlopen-based plugin module: consumers never link against it, but
        # they need to locate it in lib/abiword-3.0/plugins/
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/abiword-3.0/plugins"]
