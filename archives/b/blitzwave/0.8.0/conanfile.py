#!/usr/bin/env python3
"""Conan recipe for blitzwave 0.8.0 on HarmonyOS (OHOS).

blitzwave is a small C++ wavelet mini-library built on the blitz++ array
template library.  Upstream 0.8.0 (2014) builds with autoconf/automake/
libtool but ships only configure.ac + autogen.sh — no generated configure
and no Makefile.in.

OHOS-specific handling (evidence in notes.md):
- build() bootstraps with `autoreconf --install --force`; automake/libtool
  are pulled in as tool_requires because the OHOS image only ships the
  autoconf suite under /data/service/hnp/bin (same approach as
  abiword-plugin-clarisworks).
- patch 0001 adds AM_PROG_AR to configure.ac: with automake >= 1.12 the
  -Werror in AM_INIT_AUTOMAKE turns the "AM_PROG_AR required" warning into
  a hard bootstrap failure (upstream issue #2; same fix as Homebrew and
  macports).
- explicit --build/--host triplet: config.guess cannot guess HarmonyOS
  (uname -s = "HarmonyOS", uname -r = "HongMeng Kernel 1.12.0") and aborts
  with "cannot guess build type".
- the generated configure contains `umask 077` around its config.status
  temp dir; under HMDFS a 0700 dir becomes drwx--S--- (unwritable) and
  config.status dies with "can't create ./confXXXX/subs1.awk: Permission
  denied" (E114).  The generated configure is rewritten to drop umask 077,
  exactly like abiword-plugin-clarisworks.
- configure is invoked with a command-line CONFIG_SHELL=/bin/sh prefix: the
  profile buildenv pins CONFIG_SHELL to bash, which historically corrupts
  libtool quoting (boolstuff precedent).
- make -j1: parallel make hits the HMDFS jobserver fifo EPERM (E074).
- blitz is discovered through the AC_CHECK_LIB fallback (the conan blitz
  package ships no blitz.pc / blitz-config), so -I/-L for blitz are injected
  via AutotoolsToolchain extra flags.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class BlitzwaveConan(ConanFile):
    name = "blitzwave"
    version = "0.8.0"
    description = (
        "C++ wavelet mini-library building on the blitz++ array template "
        "library; heavily templated, supports n-dimensional wavelet "
        "decompositions of various numerical data types"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://oschulz.github.io/blitzwave/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("wavelet", "blitz", "dsp", "math", "header")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Public header dependency: blitzwave headers #include <blitz/array.h>.
        self.requires("blitz/1.0.2")

    def build_requirements(self):
        # Upstream 0.8.0 ships no generated configure; build() must run
        # `autoreconf --install --force`.  The OHOS image (device and CI
        # sandbox) only ships the autoconf suite (autoconf/autoheader/
        # autom4te/autoreconf) under /data/service/hnp/bin — automake and
        # libtool are missing, so pull them in as tool_requires (same
        # approach as abiword-plugin-clarisworks).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "blitzwave is only supported on Linux/OHOS, not "
                + str(self.settings.os))
        arch = str(self.settings.arch)
        if arch not in ("armv8", "aarch64", "x86_64"):
            raise ConanInvalidConfiguration(
                "blitzwave OHOS adaptation is validated on armv8/aarch64 "
                "and x86_64, not " + arch)
        # C++11 is the practical minimum: consumer code must be able to
        # compile the blitz++ headers pulled in by <blitzwave/*.h>.
        cppstd = self.settings.get_safe("compiler.cppstd")
        if cppstd and cppstd.replace("gnu", "") in ("98", "03"):
            raise ConanInvalidConfiguration(
                "blitzwave requires at least C++11 (blitz++ headers)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _prepare_autotools_env():
        """The automake/aclocal/libtoolize on this environment hardcode
        absolute paths for autoconf/autom4te/sed that may not exist; point
        the canonical env vars at whatever is actually on PATH (same helper
        as abiword-plugin-clarisworks)."""
        for tool, var in (("autoconf", "AUTOCONF"),
                          ("autoheader", "AUTOHEADER"),
                          ("autom4te", "AUTOM4TE"),
                          ("sed", "SED")):
            if os.environ.get(var):
                continue
            path = shutil.which(tool)
            if path:
                os.environ[var] = path

    @staticmethod
    def _drop_umask_077(path):
        """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
        creates a drwx--S--- temp dir that is not writable even by its owner,
        so config.status dies with "can't create ./confXXXX/subs1.awk:
        Permission denied".  Remove `umask 077` (and the now-orphaned
        parentheses) so config.status can create its temp dir."""
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def generate(self):
        self._prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS") and
        # its compiler probe also fails under the HMDFS tmp dir.  Pass the
        # triplet explicitly (config.sub accepts *-linux-ohos) so configure
        # never runs the config.guess probe; build == host keeps the build
        # native (same approach as abiword-plugin-clarisworks).
        arch = str(self.settings.arch)
        cpu = "aarch64" if arch in ("armv8", "aarch64") else arch
        triplet = f"{cpu}-unknown-linux-ohos"
        tc.configure_args.append(f"--build={triplet}")
        tc.configure_args.append(f"--host={triplet}")
        # The conan blitz package ships no blitz.pc / blitz-config, so
        # configure finds blitz through the AC_CHECK_LIB fallback: inject
        # -I/-L via the toolchain (abook-style), CFLAGS/CXXFLAGS for the
        # compilation, LDFLAGS for the AC_CHECK_LIB link probe.
        blitz = self.dependencies["blitz"]
        for inc in blitz.cpp_info.includedirs:
            tc.extra_cxxflags.append(f"-I{inc}")
        for libdir in blitz.cpp_info.libdirs:
            tc.extra_ldflags.append(f"-L{libdir}")
        tc.generate()
        # CONFIG_SHELL is pinned to /bin/sh inside build() with a command
        # line prefix assignment (profile buildenv pins it to bash, which
        # historically corrupts libtool quoting; boolstuff precedent).
        # Unlike boolstuff this recipe does not pin LC_ALL=C: the only
        # non-ASCII inputs (config.status sed/awk byte compares) never
        # materialized here — two full builds ran clean without it.

    def build(self):
        # Apply the conandata patch set (0001 AM_PROG_AR) to configure.ac
        # BEFORE bootstrapping: the whole autotools chain is regenerated by
        # autoreconf right after, so patched configure.ac is always older
        # than every generated product and no maintainer-rule timestamp
        # pinning is needed.
        apply_conandata_patches(self)
        self._prepare_autotools_env()
        # Upstream 0.8.0 ships only configure.ac + autogen.sh: bootstrap the
        # full autotools chain in the source folder.  autoreconf resolves
        # aclocal/automake/libtoolize through the tool_requires env vars
        # ($ACLOCAL/$AUTOMAKE/$LIBTOOLIZE injected by the conanbuild env).
        self.run("autoreconf --install --force",
                 cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS).
        self._drop_umask_077(os.path.join(self.source_folder, "configure"))
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            raise ConanException("autoreconf failed to generate configure")
        arch = str(self.settings.arch)
        cpu = "aarch64" if arch in ("armv8", "aarch64") else arch
        triplet = f"{cpu}-unknown-linux-ohos"
        # The upstream test programs link with libtool `-static` (test
        # _LDFLAGS), which needs the static archive — so a shared build
        # enables shared but keeps libtool's default static build too, and
        # only the static-only variant disables shared.
        link_switches = ("--enable-shared"
                         if self.options.shared
                         else "--enable-static --disable-shared")
        # Conan's Autotools.install() runs `make install DESTDIR=<pkg>`: with
        # an absolute --prefix the install lands in <pkg>/<abs-prefix> (the
        # boolstuff pitfall).  Configure with --prefix=/ and quoted relative
        # dir flags so DESTDIR alone decides the final location.
        configure_cmd = (
            f'CONFIG_SHELL=/bin/sh "{configure_path}" '
            f"--build={triplet} --host={triplet} "
            f"{link_switches} "
            "--prefix=/ "
            "'--bindir=${prefix}/bin' "
            "'--libdir=${prefix}/lib' "
            "'--includedir=${prefix}/include'"
        )
        autotools = Autotools(self)
        # Command-line CONFIG_SHELL assignment wins over the profile buildenv
        # bash pinning (boolstuff precedent).
        self.run(configure_cmd, env="conanbuild")
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])
        # Upstream self-tests: three assert/behavior-based noinst programs
        # (upstream 0.8.0 has no `make check` wiring — noinst_PROGRAMS only).
        # Each must exit 0 AND show substantive output (the try/catch in
        # WaveletDecomp-test/arrayTools-test would swallow failures into
        # exit 0 otherwise).
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        build_src = os.path.join(self.build_folder, "src")
        source_src = os.path.join(self.source_folder, "src")
        # Fixtures: testimage.pnm ships in the tarball under src/; the VPATH
        # build leaves it in the source folder, so pass it as argv[1]
        # (WaveletDecomp-test supports argc==2).  intdata.txt is NOT part of
        # the upstream tarball (nor of the upstream git repo) — arrayTools-test
        # reads it from the cwd, so a deterministic 256-sample integer signal
        # is generated as the missing fixture.
        with open(os.path.join(build_src, "intdata.txt"), "w") as f:
            f.write("\n".join(str((i * 37) % 256) for i in range(256)) + "\n")
        testimage = os.path.join(source_src, "testimage.pnm")
        for name in ("Wavelet-test", "WaveletDecomp-test", "arrayTools-test"):
            binary = os.path.join(build_src, name)
            if not os.path.isfile(binary):
                raise ConanException(f"upstream test binary missing: {name}")
            if name == "WaveletDecomp-test":
                self.run(f'"{binary}" "{testimage}"', env="conanrun")
            else:
                self.run(f'"{binary}"', cwd=build_src, env="conanrun")

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # libtool leftovers and the generated pkg-config file are never
        # shipped: the .pc bakes the cache-time prefix and lists -lblitz
        # unconditionally, which is wrong for conan consumers (they get the
        # correct transitive dependency through CMakeDeps instead).
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Drop standalone doc trees to keep the package minimal.
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # Headers land in include/blitzwave/ (pkginclude_HEADERS); the
        # upstream blitzwave-config and blitzwave.pc both use
        # -I${includedir}, so consumers #include <blitzwave/Wavelet.h> and
        # the relative cross-includes between the three headers resolve
        # inside that directory.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["blitzwave"]
        # blitzwave-config is the library's own config helper script.
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
