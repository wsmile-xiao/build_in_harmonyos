#!/usr/bin/env python3
"""Conan recipe — psocksxx 1.1.1 (autotools).

psocksxx is a small C++ POSIX socket wrapper library (libtool + autotools).
The GitHub tag archive ships no generated `configure`, so build() bootstraps
via `autoreconf -fi` with automake/libtool pulled in as tool_requires (the
CI sandbox lacks them; same scheme as the merged abiword-plugin-* recipes).

OHOS notes:
  - config.guess cannot identify HarmonyOS, so the aarch64 triplets are
    passed explicitly and configure never runs the probe; HMDFS setgid
    directories break `umask 077` temp-dir creation inside the generated
    configure (E114) — the generated script is patched right after
    autoreconf.
  - Upstream `make check` builds a CppUnit TAP runner (7 suites / 49 tests,
    loopback TCP/UDP + unix-socket echo) and runs it in build(). The conan
    cppunit package ships no `cppunit-config` probe script, which is what
    AM_PATH_CPPUNIT looks for via AC_PATH_PROG — a minimal shim is
    generated into PATH so the tests are enabled, built and executed here.
    Nothing test-related ships in the package.
  - Static only (--disable-shared): libtool .la files bake absolute libdir
    paths and are removed from the package, as is the generated .pc.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that may not exist in this environment.  Point the
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


class PsocksxxConan(ConanFile):
    name = "psocksxx"
    version = "1.1.1"
    description = "C++ POSIX socket wrapper library (stream, address and timeout classes)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/uditha-atukorala/psocksxx"
    url = "https://github.com/uditha-atukorala/psocksxx"
    topics = ("socket", "network", "stream", "cpp")
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"psocksxx supports Linux/OHOS only, got {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # GitHub tag archive has no `configure`: bootstrap with autoreconf.
        # tool_requires resolve with the *build* profile (same machine here).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # CppUnit is needed only to build/run the upstream TAP test runner.
        self.tool_requires("cppunit/1.15.1")

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS");
        # pass the triplets explicitly so configure never runs the probe
        # (same approach as the merged abiword-plugin-* recipes).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        # psocksxx (2015) uses dynamic exception specifications (`throw(X)`),
        # which C++17 removed — 16 hard errors in nsockaddr alone. Compile
        # as C++14, the last standard where they are still valid; the extra
        # flag is appended after the profile's -std=c++17 so the later flag
        # wins under clang.
        tc.extra_cxxflags.append("-std=c++14")
        tc.generate()

    def _route_shell_off_hnp_bash(self):
        # E386 (经验汇总 §12.38): the ohos-aarch64 profile [buildenv] pins
        # SHELL/CONFIG_SHELL to the hnp bash, which cannot getcwd() inside
        # HMDFS build dirs — configure dies with "working directory cannot
        # be determined". Rewriting the aggregated conanbuild.sh (rather
        # than sourcing a second Environment under the same script name)
        # matters: a second save_script("conanbuild") makes the aggregated
        # script source itself in an endless loop (every level re-runs the
        # toolchain prologue until exec fails with "Argument list too
        # long"). Runs before the first self.run() so every application of
        # the env sees the patched script. The profile SHELL lands in the
        # aggregated conanbuildenv-*.sh (sourced BY conanbuild.sh), so patch
        # every env script in the generators folder.
        import glob
        for script in glob.glob(os.path.join(self.generators_folder, "*.sh")):
            with open(script, "r", encoding="utf-8") as f:
                data = f.read()
            patched = data.replace("/data/service/hnp/bin/bash", "/bin/sh")
            if patched != data:
                with open(script, "w", encoding="utf-8") as f:
                    f.write(patched)
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"

    def _cppunit_paths(self):
        cppunit = self.dependencies.build["cppunit"]
        include = os.path.join(cppunit.package_folder, "include")
        lib = os.path.join(cppunit.package_folder, "lib")
        return include, lib

    def _install_cppunit_config_shim(self):
        # AM_PATH_CPPUNIT probes `cppunit-config` with AC_PATH_PROG and then
        # asks it for --version/--cflags/--libs; the conan cppunit package
        # ships no such script, so provide a minimal one pointing at the
        # conan package. Without it configure silently disables the tests
        # (HAVE_CPPUNIT false) and `make check` would execute nothing.
        include, lib = self._cppunit_paths()
        shim_dir = os.path.join(self.build_folder, "cppunit-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "cppunit-config")
        with open(shim, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write('case "$1" in\n')
            f.write('  --version) echo "1.15.1" ;;\n')
            f.write('  --cflags) echo "-I{}" ;;\n'.format(include))
            f.write('  --libs) echo "-L{} -lcppunit -ldl" ;;\n'.format(lib))
            f.write('  *) echo "usage: cppunit-config [--version|--cflags|--libs]" >&2; exit 1 ;;\n')
            f.write("esac\n")
        os.chmod(shim, 0o755)
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
        return lib

    def build(self):
        self._route_shell_off_hnp_bash()
        _prepare_autotools_env()
        cppunit_libdir = self._install_cppunit_config_shim()
        # test headers: unix-socket paths off the read-only /tmp (OHOS)
        apply_conandata_patches(self)
        # GitHub tag archive has no `configure`: generate one (source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Upstream test suite: `make check` builds and runs the CppUnit TAP
        # runner (tap-runner.tap). 14 of the 49 atomic cases cannot pass on
        # OHOS (full analysis in notes.md):
        #   - 13 local-domain socket cases: AF_UNIX bind() is denied
        #     platform-wide (EPERM/EACCES in every writable location —
        #     verified by direct probe, see notes.md);
        #   - 1 DNS case (nsockaddr_test::test_constructor_fail): the device
        #     resolver wildcard-answers invalid names (ping invalid.domain →
        #     198.18.10.6), so the expected sockexception never throws.
        # Run the suite, then verify the documented baseline from
        # test-suite.log — failures are accounted for, not swallowed.
        self.run(
            'LD_LIBRARY_PATH="${{LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}}"{} make check -j1 || true'.format(
                cppunit_libdir),
            cwd=self.build_folder,
            env="conanbuild",
        )
        self._verify_upstream_baseline()

    def _verify_upstream_baseline(self):
        import re
        log_path = os.path.join(self.build_folder, "test", "test-suite.log")
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        def count(key):
            m = re.search(r"^#\s+{}:\s+(\d+)".format(key), content, re.M)
            return int(m.group(1)) if m else -1

        total, passed, failed = count("TOTAL"), count("PASS"), count("FAIL")
        self.output.info(
            "upstream make check baseline: TOTAL={} PASS={} FAIL={}".format(
                total, passed, failed))
        # Device evidence: 35 pass / 14 platform-limited failures. The CI
        # worker sandbox is less restrictive (it allows AF_UNIX bind and has
        # no DNS wildcard), so only the floor is asserted here — every case
        # must still execute and at least the device-verified 35 must pass.
        if total != 49 or passed < 35 or failed > 14:
            tail = "\n".join(content.splitlines()[-40:])
            raise ConanException(
                "upstream test baseline mismatch (expected TOTAL=49 and "
                "PASS>=35 and FAIL<=14):\n" + tail)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool .la / .pc bake absolute paths (autotools checklist #6).
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for f in os.listdir(libdir):
                path = os.path.join(libdir, f)
                if f.endswith(".la"):
                    os.remove(path)
        pcdir = os.path.join(libdir, "pkgconfig")
        if os.path.isdir(pcdir):
            for f in os.listdir(pcdir):
                if f.endswith(".pc"):
                    os.remove(os.path.join(pcdir, f))
        # Upstream ships no COPYING; the licence notice lives in the source
        # headers (LGPL-3.0-or-later) and README.md.
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["psocksxx"]
