#!/usr/bin/env python3
"""Conan recipe — ykclient 2.15 (Yubico OTP validation C client library).

Adaptation scope (HarmonyOS PC / OHOS aarch64):
- autotools build of libykclient (+ vendored base64/sha1 sources), shared
  option following the repo library convention (default static);
- upstream test suite: tests/selftest.c wired via automake `TESTS`, executed
  by `make check` inside build() (hard rule: upstream tests really run).
  The suite carries upstream's own offline switch TEST_WITHOUT_INTERNET:
  the file has 36 TEST() marker sites, 9 of which sit in upstream's own
  `#if 0` dead code, leaving 27 active ones.  Six of those 27 are *inside*
  `#ifndef TEST_WITHOUT_INTERNET`, so defining the switch compiles them out
  and 21 marker sites run.  Of those 21, 15 contain a network assertion that
  takes upstream's own "Test SKIPPED" branch (16 SKIPPED lines in total;
  selftest.c:317 loops and prints twice) because they validate against
  api.yubico.com wsapi v1 - an endpoint retired upstream (HTTP 403 today);
  the remaining 6 are pure offline assertions and run in full.
- dependency: libcurl via PKG_CHECK_MODULES -> PkgConfigDeps + PKG_CONFIG_PATH
  injected into the build env (E468: append generators folder before
  VirtualBuildEnv so the env file carries the path).

Known OHOS/platform pitfalls handled here (repo knowledge base):
- the git archive ships no `configure`: build() runs `autoreconf -fi`
  (automake/libtool pulled in as tool_requires, same as
  abiword-plugin-clarisworks 3.0.8);
- E114: generated configure patched to drop `umask 077` (HMDFS setgid dirs);
- E074: make runs -j1 (HMDFS jobserver fifo EPERM);
- E007 family: not needed here — autoreconf -fi installs the current
  automake config.guess/config.sub, which know aarch64-*-linux-ohos; the
  explicit triplet keeps configure from running the config.guess probe.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that may not exist; point env at PATH hits."""
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
    creates an unwritable drwx--S--- temp dir. Remove the `umask 077`
    (and its now-orphaned parentheses) from the generated configure."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)



def _route_shell_off_hnp_bash(conanfile):
    """E386 (经验汇总 §12.38 / §12.70-1, psocksxx/1.1.1 先例): the ohos-aarch64
    profile pins SHELL/CONFIG_SHELL to /data/service/hnp/bin/bash, whose
    getcwd() fails inside HMDFS build dirs, so configure dies with
    "working directory cannot be determined". Rewrite every aggregated env
    script in the generators folder instead: a second
    save_script("conanbuild") would make the script source itself in an
    endless loop. Must run before the first self.run().
    """
    import glob
    for script in glob.glob(os.path.join(conanfile.generators_folder, "*.sh")):
        with open(script, "r", encoding="utf-8") as f:
            data = f.read()
        patched = data.replace("/data/service/hnp/bin/bash", "/bin/sh")
        if patched != data:
            with open(script, "w", encoding="utf-8") as f:
                f.write(patched)
    os.environ["CONFIG_SHELL"] = "/bin/sh"
    os.environ["SHELL"] = "/bin/sh"


class YkclientConan(ConanFile):
    name = "ykclient"
    version = "2.15"
    description = "Yubico C client library for YubiKey OTP validation"
    license = "BSD-2-Clause"
    homepage = "https://developers.yubico.com/yubico-c-client/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0.1")

    def build_requirements(self):
        # The git archive ships no `configure`: build() must run
        # `autoreconf -fi`. The build host lacks automake/aclocal/libtoolize
        # as conan-managed tools, so pull them in via tool_requires (resolved
        # with the build profile; pass both -pr:h and -pr:b to conan create).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ykclient is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        # pkg_check_modules(libcurl) discovery: emit .pc files for conan
        # deps and put the generators folder on PKG_CONFIG_PATH. Must run
        # BEFORE VirtualBuildEnv so the env file carries the path (E468).
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH",
                                       self.generators_folder)
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly
        # (config.sub installed by autoreconf knows *-linux-ohos).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Upstream's own offline switch: with it defined, 6 TEST() sites are
        # compiled out, 15 of the remaining 21 print "Test SKIPPED" for their
        # network assertion and 6 run purely offline assertions.
        tc.extra_cflags.append("-DTEST_WITHOUT_INTERNET")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        _route_shell_off_hnp_bash(self)
        # The git archive ships no `configure`: bootstrap it (source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        # E289: no help2man on OHOS; HELP2MAN=true alone still breaks install
        # (ykclient.1 never gets created), so clear dist_man_MANS as well.
        autotools.make(args=["-j1", "HELP2MAN=/bin/true", "dist_man_MANS="])
        # musl's loader ignores DT_RUNPATH (§12.2): selftest DT_NEEDEDs
        # libcurl.so, so the dependency libdir must be on LD_LIBRARY_PATH
        # (llvm-readelf shows libcurl.so itself needs only libc). Precedent:
        # acedb/4.9.62, 4ti2/1.6.10.
        ld = [os.path.join(dep.package_folder, d)
              for dep in self.dependencies.host.values() if dep.package_folder
              for d in dep.cpp_info.libdirs]
        ld += [self.build_folder,
               os.path.join(self.build_folder, ".libs"),
               os.path.join(self.build_folder, "tests", ".libs")]
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld) + ((":" + prev) if prev else "")
        # R51 hard rule: run the upstream test suite (`make check` ->
        # automake TESTS = tests/selftest) with the offline switch above.
        # VPATH: automake gives tests/ only `-I. -I$(srcdir)` (no
        # -I$(top_builddir)`), so configure-generated ykclient_version.h
        # is invisible to `make check`. INCLUDES is a free append slot in
        # both generated Makefiles; AM_CPPFLAGS is not (root Makefile.am
        # uses it for $(LIBCURL_CFLAGS)).
        autotools.make(
            target="check",
            args=["-j1", "HELP2MAN=/bin/true", "dist_man_MANS=",
                  "INCLUDES=-I" + self.build_folder])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["HELP2MAN=/bin/true", "dist_man_MANS="])

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["ykclient"]
        # The package also installs the upstream  CLI (bin/ykclient),
        # so declare bindirs: R38/CI L0k check the delivered artifacts, and the
        # preflight PF8 gate treats a recipe with non-empty bindirs as a CLI
        # package and then requires archives/y/ykclient/commands.json.
        self.cpp_info.bindirs = ["bin"]
        # static consumers must also link libcurl (shared mode records it
        # via the .so's own DT_NEEDED, but keep it explicit for consumers)
        if not self.options.shared:
            self.cpp_info.requires = ["curl::curl"]
