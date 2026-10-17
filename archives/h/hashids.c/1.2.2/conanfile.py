#!/usr/bin/env python3
"""Conan recipe — hashids.c 1.2.2.

Small C library generating Youtube-like short IDs from one or many numbers
(https://hashids.org/).  The build produces libhashids (libhashids.a/.so) plus
the `hashids` command-line tool and the `test` upstream test program.

Build system: autotools.  The GitHub tag archive ships no generated
`configure` script, so build() runs `autoreconf -fi` first (automake/libtool
pulled in as tool_requires; same approach as abiword-plugin-clarisworks).

OHOS adaptations:
  - R32: settings.os validated against ("Linux", "OHOS").
  - E114: the generated configure keeps `umask 077 && mktemp -d` in
    config.status; HMDFS turns the 0700 temp dir into an unwritable
    drwx--S--- dir, so the umask is dropped from the generated configure.
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
  - `make check` runs the upstream `test` program (L1 upstream test).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist here; point the env vars at
    whatever is actually on PATH.  Also prepend the OHOS tool dirs to PATH
    (E540: CC/CXX come from the profile, but later recipe commands like
    make/autoreconf resolve through PATH and fail if the runner PATH lacks
    /data/service/hnp/bin)."""
    tool_paths = [
        "/data/service/hnp/bin",
        "/data/service/hnp/cmake.org/cmake_4.1.2/bin",
    ]
    extra = [p for p in tool_paths if p and os.path.isdir(p)]
    cur = os.environ.get("PATH", "")
    os.environ["PATH"] = ":".join(extra + [cur]) if extra else cur
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
    creates a drwx--S--- temp dir not writable even by its owner.  Drop the
    umask so config.status can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class HashidsCConan(ConanFile):
    name = "hashids.c"
    version = "1.2.2"
    description = "Hashids short-ID generation C library (encode/decode numbers to short strings)"
    license = "MIT"
    homepage = "https://github.com/tzvetkoff/hashids.c"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "hashids.c is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def build_requirements(self):
        # The GitHub tag archive ships no generated `configure`: build() must
        # run `autoreconf -fi`.  The build host lacks automake/aclocal/
        # libtoolize (only the autoconf suite is under /data/service/hnp/bin),
        # so pull them in as tool_requires (same approach as
        # abiword-plugin-clarisworks / argp-standalone).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dependency-free: only libc (LIBM)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static linking
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel"): pass the triplet explicitly so configure
        # never runs the build-type probe (same approach as
        # abiword-plugin-clarisworks / argp-standalone).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # No generated configure in the tag archive: bootstrap it.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # L1: run the upstream test program (src/test.c, TESTS=test)
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.install(args=["-j1"])

    def package_info(self):
        # lib_LTLIBRARIES = libhashids.la -> linked as -lhashids
        self.cpp_info.libs = ["hashids"]
