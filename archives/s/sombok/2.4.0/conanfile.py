#!/usr/bin/env python3
"""Conan recipe — sombok 2.4.0.

Builds libsombok (UAX #14 line-breaking / grapheme-cluster C library) and
the `sombok` command-line tool for HarmonyOS PC.

OHOS adaptations:
  - the git tag archive ships no `configure`, so build() runs
    `autoreconf -fi`; the minimal OHOS image lacks automake/aclocal/libtoolize
    (only the autoconf suite is present under /data/service/hnp/bin), so
    automake + libtool are pulled in as tool_requires (same approach as
    abiword-plugin-* / argp-standalone); tool_requires resolve with the
    *build* profile, so both -pr:h and -pr:b must reach conan create;
  - the installed automake/aclocal hardcode absolute paths for
    autoconf/autom4te/sed that do not exist here — AUTOCONF/AUTOHEADER/
    AUTOM4TE/SED are pointed at the PATH copies (E007-style);
  - the generated configure is patched at build time to drop `umask 077`
    from the config.status temp-dir creation (E114: HMDFS setgid turns a
    0700 temp dir into an unwritable drwx--S--- dir);
  - libthai support is explicitly disabled (optional Thai ICU tail; the
    OHOS environment has no libthai and configure would auto-disable it
    anyway — pin it for reproducibility);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - `make check` runs the full upstream Perl suite (tests/*.t, 35 test
    cases) against the test-data corpus (git submodule, fetched from the
    upstream commit pinned in conandata.yml — archives do not include
    submodules).

Upstream test suite accounting (see notes.md):
  tests/01break.t  plan 13, 02hangul.t plan 2, 03ns.t plan 3, 05urgent.t
  plan 5, 06context.t plan 2, 07sea.t plan 1, 09uri.t plan 2, 11format.t
  plan 6, 14sea_al.t plan 1  =>  N_static = 35 (TAP plan lines).
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


def _drop_umask_077(path):
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


class SombokConan(ConanFile):
    name = "sombok"
    version = "2.4.0"
    description = "Sombok: Unicode UAX #14 line-breaking and grapheme-cluster library"
    license = ("GPL-2.0-or-later", "Artistic-1.0-OR-GPL-1.0-or-later")
    homepage = "https://github.com/hatukanezumi/sombok"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    # E386/§12.38①: the profile sets CONFIG_SHELL to the hnp bash, whose
    # getcwd() fails under HMDFS build dirs (configure dies with "working
    # directory cannot be determined").  Route configure/make through
    # /bin/sh while keeping the full Conan toolchain environment
    # (direvent/5.5 precedent).
    sh = "env -u CONFIG_SHELL SHELL=/bin/sh"
    configure_args = (
        " --prefix=/"
        " '--bindir=${prefix}/bin'"
        " '--libdir=${prefix}/lib'"
        " '--includedir=${prefix}/include'"
        " --build=aarch64-unknown-linux-gnu"
        " --host=aarch64-unknown-linux-gnu"
        " --disable-libthai"
    )

    def export_sources(self):
        # conandata.yml carries no patches today; the call is kept explicit
        # so a future patch slot slots in without touching source().
        export_conandata_patches(self)

    def requirements(self):
        # dependency-free: libthai (optional Thai line-breaking tail) is
        # explicitly disabled below
        pass

    def build_requirements(self):
        # The tag archive ships no `configure`; bootstrap with autoreconf.
        # automake/aclocal/libtoolize are absent from the OHOS image.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sombok is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["sombok-2.4.0.tar.gz"],
            strip_root=True)
        # UAX #14 test corpus: git submodule at the commit the sombok-2.4.0
        # tag pins (github archives do not include submodule contents).
        get(self, **self.conan_data["sources"]["sombok-test-data-dd46a73.tar.gz"],
            destination="test-data", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        # generate() only produces the conanbuild environment (CC/CFLAGS/
        # LDFLAGS...); the configure flags live in self.configure_args and
        # are passed by hand in build() through the /bin/sh route.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        src = self.source_folder
        # no `configure` in the archive: bootstrap (in-source so the
        # tests/*.t relative `test-data/` paths and ./sombok resolve)
        self.run(f'cd "{src}" && {self.sh} autoreconf -fi')
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(src, "configure"))
        self.run(f'cd "{src}" && {self.sh} sh ./configure{self.configure_args}')
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        self.run(f'cd "{src}" && {self.sh} make -j1')
        # Upstream test suite: tests/*.t (35 TAP-planned cases) via the
        # `sombok` check_PROGRAMS binary against test-data/ corpus.
        # Non-zero exit fails the build — errors are not swallowed.
        self.run(f'cd "{src}" && {self.sh} make -j1 check')

    def package(self):
        src = self.source_folder
        self.run(f'cd "{src}" && {self.sh} make -j1 install DESTDIR="{self.package_folder}/"')

    def package_info(self):
        self.cpp_info.libs = ["sombok"]
