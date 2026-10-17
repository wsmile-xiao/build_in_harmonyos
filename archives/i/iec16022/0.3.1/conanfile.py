#!/usr/bin/env python3
"""Conan recipe — iec16022 0.3.1 (DataMatrix / ECC200 2D barcode generator).

Upstream : https://github.com/rdoeffinger/iec16022  (GPL-2.0-or-later)
Products : libiec16022  — encode an ECC200 symbol and render it as PNG, EPS,
                          hex, bitmap or plain text (iec16022ecc200/image/reedsol)
           iec16022     — command-line front-end (option parsing via popt)

Build system: Autotools.  The official GitHub *release* asset ships a fully
generated `configure` + `Makefile.in` (the git-archive tarball ships only
`configure.ac`), so no autoreconf/libtool bootstrap is required.

Dependencies
------------
popt/1.16 — the sole external dependency.  configure.ac runs
`PKG_CHECK_MODULES([POPT], [popt], , AC_SEARCH_LIBS(...))` as a hard
requirement and errors out when popt is missing.  It is consumed statically
(R26).

OHOS adaptations (patches/, all modified-file diffs)
----------------------------------------------------
0001-config.guess-harmonyos.patch
    Teach config.guess the HarmonyOS uname signature so the build identifies
    itself natively as aarch64-unknown-linux-ohos (E007/E205).  The triplet is
    deliberately *not* forced via --build/--host: that sets cross_compiling=yes
    and silently skips every AC_RUN_IFELSE probe, yielding a wrong config.h
    (E007).
0002-config.sub-ohos.patch
    Register the ohos-linux triplet, the ohos* OS family and the linux-ohos
    kernel/OS pair so the guessed triplet validates (E122).
0003-configure-tmpdir-hmdfs.patch
    HMDFS forces the setgid bit on directories, so autoconf's
    `umask 077 && mktemp -d ./confXXXXXX` produces a drwx--S--- directory that
    its own owner cannot write; config.status then dies with
    "subs1.awk: Permission denied" (E011/E114).  Relax the umask to 002.
0004-test-testsuite-vpath-srcdir.patch
    The upstream test script references its reference artefacts by bare
    filename, which cannot work in an out-of-tree (VPATH) build: `make check`
    runs the script from the build tree while the fixtures only exist in the
    source tree.  Resolve them through ${srcdir:-.} (automake exports srcdir),
    which keeps an in-source build behaving exactly as before.

Build notes
-----------
- E232: on a native HarmonyOS build host, Autotools.configure() cannot launch
  the source `configure` directly — the shebang-based exec is refused
  ("Permission denied", error 126) before Autoconf even starts.  CONFIG_SHELL
  cannot help because it is only read *by* Autoconf.  build() therefore runs
  `/system/bin/sh <configure> <autotools._configure_args>` when
  settings_build.os == "OHOS", and keeps autotools.configure() elsewhere.  The
  check is on the *build* profile: a Linux/Windows cross build targeting OHOS
  has no /system/bin/sh.
- E037/E232: for the same reason automake's test driver cannot exec
  test/testsuite.sh directly, so `make check` is invoked with
  LOG_COMPILER=/system/bin/sh.  The driver then calls `sh ./testsuite.sh` and
  the script's shebang is never consulted — no upstream test file is modified.
- make runs with -j1: a parallel jobserver needs a FIFO in TMPDIR, which HMDFS
  rejects with EPERM (E074).
- `make check` runs the upstream end-to-end suite (test/testsuite.sh): it
  encodes one fixed payload into all six output formats and diffs the results
  against the reference artefacts shipped in test/ (L1 upstream test).
  Device result: PASS, 6/6 formats byte-identical.
- libiec16022 is statically linked into the CLI by default, so the installed
  `bin/iec16022` has no runtime .so lookup requirement.
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class Iec16022Conan(ConanFile):
    name = "iec16022"
    version = "0.3.1"
    description = "DataMatrix (IEC 16022 / ECC200) 2D barcode generator library and CLI"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rdoeffinger/iec16022"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: OHOS is a Linux-like target.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS, not {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"{self.ref} supports OHOS only on armv8/aarch64")

    def requirements(self):
        # Mandatory runtime + build dependency (configure.ac hard-requires popt).
        self.requires("popt/1.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # configure probes popt through pkg-config; PkgConfigDeps materialises
        # popt.pc pointing at the real Conan package paths.
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.generate()

        if self.settings.os == "OHOS":
            # E002: /tmp is read-only on HarmonyOS.  With TMPDIR unset the
            # compiler drops its temporaries in /tmp, so AC_PROG_CC's conftest
            # fails with "C compiler cannot create executables" even though the
            # toolchain is healthy.  Point TMPDIR at a writable build-local dir.
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.vars(self, scope="build").save_script("conanbuild_tmpdir")

    def build(self):
        autotools = Autotools(self)
        if str(self.settings_build.os) == "OHOS":
            # E232: the native HarmonyOS source location rejects executing the
            # `configure` script directly (shebang-based exec), so
            # Autotools.configure() dies with "Permission denied" / error 126
            # before Autoconf ever starts.  CONFIG_SHELL cannot help — it is
            # only read *by* Autoconf, i.e. after that first process has
            # already been launched.  Launch it through the system shell
            # instead, keeping autotools._configure_args authoritative.
            # Keyed on settings_build (the executor), not settings (the target):
            # a Linux/Windows cross build targeting OHOS has no /system/bin/sh.
            configure = os.path.join(self.source_folder, "configure")
            shell = "/system/bin/sh"
            if not os.path.isfile(shell):
                raise ConanException(f"Required OHOS shell is missing: {shell}")
            environment = Environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            with environment.vars(self).apply():
                self.run(f'"{shell}" "{configure}" {autotools._configure_args}')
                # E074: a parallel make needs a jobserver FIFO, which HMDFS
                # rejects with EPERM.
                autotools.make(args=["-j1"])
                # L1: upstream end-to-end suite — all six output formats
                # compared against the reference artefacts shipped in test/.
                #
                # E037/E232: HarmonyOS refuses to launch scripts via their
                # shebang, so automake's test driver cannot exec
                # test/testsuite.sh directly ("bad interpreter: Permission
                # denied", exit 126).  LOG_COMPILER makes the driver run
                # `$(LOG_COMPILER) ./testsuite.sh` instead, i.e. the script is
                # handed to the shell as an argument and its shebang is never
                # consulted.  This keeps `make check` authoritative — no
                # upstream test file has to be modified.
                autotools.make(
                    target="check",
                    args=["-j1", f"LOG_COMPILER={shlex.quote(shell)}"])
        else:
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Drop libtool wrappers: they embed absolute build paths and are not
        # relocatable (E236).
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["iec16022"]
        # Upstream installs the headers under <prefix>/include/iec16022 and its
        # own libiec16022.pc declares `Cflags: -I${includedir}/iec16022`, so
        # consumers write `#include <iec16022ecc200.h>`.  Keep "include" as a
        # second root so `#include <iec16022/...>` also works.
        self.cpp_info.includedirs = ["include/iec16022", "include"]
        # The CLI front-end ships in bin/; declared at the software level in
        # commands.json (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libiec16022")
        self.cpp_info.set_property("cmake_file_name", "iec16022")
        self.cpp_info.set_property("cmake_target_name", "iec16022::iec16022")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
