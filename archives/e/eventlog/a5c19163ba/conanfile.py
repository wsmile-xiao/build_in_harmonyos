#!/usr/bin/env python3
"""Conan recipe for eventlog a5c19163ba (Autotools).

- The GitHub archive ships no generated `configure`, so build() runs
  `autoreconf -fi` to bootstrap (upstream commits only configure.in/Makefile.am);
- the generated config.status temp-dir creation keeps `umask 077`, which HMDFS
  turns into an unwritable drwx--S--- dir (E114), so it is patched out;
- make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
- upstream tests (tests/evtrec, evtfmt, evtsyslog, evtsyslog-macros) are
  noinst_PROGRAMS with no TESTS registration; they are run manually.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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


class EventlogConan(ConanFile):
    name = "eventlog"
    version = "a5c19163ba"
    description = "eventlog a5c19163ba - syslog event log library"
    license = "MIT"
    homepage = "https://github.com/balabit/eventlog"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The git archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize, so pull
        # them in as tool_requires (same approach as argp-standalone and
        # abiword-plugin-clarisworks).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "eventlog is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
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
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The git archive ships no `configure`: generate one from
        # configure.in (run in source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Run upstream noinst test programs (built in the build folder)
        for test in ("evtrec", "evtfmt", "evtsyslog", "evtsyslog-macros"):
            self.run("./" + test, cwd=os.path.join(self.build_folder, "tests"),
                     env="conanrun")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["evtlog"]
