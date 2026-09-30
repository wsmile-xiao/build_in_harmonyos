#!/usr/bin/env python3
"""Conan recipe — lcmaps-plugins-basic 1.7.1 (Autotools, LCMAPS evaluation plugins)

Notes:
- Pure autotools: the release tarball ships a complete pre-generated configure
  (no autoreconf — knowledge E089: device aclocal is broken, tarball aclocal.m4
  is complete).
- Upstream product: 7 LCMAPS evaluation plugins built as versionless loadable
  modules (-module -avoid-version): liblcmaps_dummy_bad.so,
  liblcmaps_dummy_good.so, liblcmaps_ban_dn.so, liblcmaps_localaccount.so,
  liblcmaps_poolaccount.so, liblcmaps_posix_enf.so, liblcmaps_ldap_enf.so,
  installed into <prefix>/lib/lcmaps/ (moduledir). install-data-hook creates a
  lcmaps_<mod>.mod symlink (or copy fallback, patches/0004, knowledge E018)
  per plugin — that is the file name the LCMAPS framework dlopen()s.
- Dependencies (both already ported in this repository):
  * lcmaps/1.6.7 — the without-GSI framework. configure discovers the plugin
    headers via `--with-lcmaps-prefix` (the direct header-compile route of
    AC_LCMAPS_INTERFACE([basic]); the pkg-config route alone returns
    -I//include because the packaged .pc carries prefix=/ — see below).
    OHOS musl dlopen scope adaptation: a dlopen()ed DSO resolves undefined
    symbols ONLY against its own DT_NEEDED closure on this platform (probed;
    not the main program, its startup libs, nor RTLD_GLOBAL dlopen'd
    objects), so upstream's "plugin symbols come from the caller" model
    cannot relocate under RTLD_NOW. The recipe therefore links every plugin
    with -llcmaps_without_gsi (explicit DT_NEEDED on the framework — always
    satisfied in real use since the framework loads the plugins).
  * openldap/2.6.7 — ldap_enf plugin hard dependency: configure runs an
    unconditional AC_CHECK_HEADER([ldap.h]) (no opt-out switch) and the
    liblcmaps_ldap_enf target links -lldap.
  * dl: AC_CHECK_LIB([dl],[dlopen]) hard check passes on the OHOS toolchain
    (musl: dl* API in libc, -ldl probe links; knowledge E013).
  * No OpenSSL/gsoap/voms/pam/globus dependency in this flavour.
- Link closure is explicit (build-chain-pitfalls "shared library link closure"):
  every host dependency libdir is added as -L and -Wl,-rpath-link before the
  toolchain environment snapshot; no reliance on implicit DT_NEEDED closure
  search or device default paths.
- E075 trap: C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH are unset for the
  build environment; otherwise pkg-config filters the -I out of
  `pkg-config --cflags lcmaps-basic-interface` and configure finds no headers.
- Upstream has NO automated test suite (discovery: no check target/TESTS/
  check_PROGRAMS in any Makefile.am; the 5 src/*/plugin_test.c programs are
  EXTRA_DIST manual clients). OHOS verification lives in test_package/test.c:
  dlopen() of the framework (RTLD_GLOBAL) followed by each installed .mod
  module (musl dynamic-loading adaptation point, E013) + dlsym() of the three
  plugin entry points (plugin_initialize/plugin_run/plugin_terminate) +
  packaged artifact manifest checks.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcmapsPluginsBasicConan(ConanFile):
    name = "lcmaps-plugins-basic"
    version = "1.7.1"
    description = (
        "LCMAPS basic evaluation plugins (dummy_bad, dummy_good, ban_dn, "
        "localaccount, poolaccount, posix_enf, ldap_enf) for the without-GSI "
        "LCMAPS framework"
    )
    license = "Apache-2.0"
    url = "https://software.nikhef.nl/security/lcmaps-plugins-basic/"
    homepage = "https://github.com/Nikhef-lcaae/lcmaps"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lcmaps/1.6.7")
        self.requires("openldap/2.6.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _abs_dirs(cpp_info, kind):
        dirs = []
        pkg = getattr(cpp_info, "package_folder", None)
        for d in getattr(cpp_info, kind, []) or []:
            dirs.append(d if os.path.isabs(d) or not pkg else os.path.join(pkg, d))
        for comp in (getattr(cpp_info, "components", None) or {}).values():
            for d in getattr(comp, kind, []) or []:
                dirs.append(d if os.path.isabs(d) or not pkg else os.path.join(pkg, d))
        return dirs

    def generate(self):
        tc = AutotoolsToolchain(self)

        lcmaps_pkg = self.dependencies["lcmaps"].package_folder

        # lcmaps headers: use the upstream-native --with-lcmaps-prefix so
        # AC_LCMAPS_INTERFACE([basic]) runs its DIRECT header-compile check
        # with -I<lcmaps_pkg>/include. The pkg-config route alone is NOT
        # enough: the packaged lcmaps-basic-interface.pc carries prefix=/
        # (lcmaps/1.6.7 is installed via conan's --prefix=/ + DESTDIR scheme),
        # so `pkg-config --cflags lcmaps-basic-interface` returns -I//include
        # and every lcmaps/*.h include fails at compile time (CI run2:
        # fatal error: 'lcmaps/lcmaps_modules.h' file not found).
        tc.configure_args.append("--with-lcmaps-prefix=%s" % lcmaps_pkg)

        # NOTE: AutotoolsToolchain.environment() is a factory (returns a fresh
        # Environment each call) — mutations on a returned object are silently
        # dropped unless the populated env is passed back into tc.generate().
        # Start from the toolchain default env (CC/CFLAGS/... included), add
        # our build-environment fixes, then generate with that env explicitly.
        # All edits happen BEFORE the environment snapshot (tc.generate).
        env = tc.environment()

        # E075: if C_INCLUDE_PATH/LIBRARY_PATH leak into the build environment,
        # pkg-config filters matching -I flags out of --cflags and configure
        # finds no lcmaps headers (LCMAPS_CFLAGS empty). Remove them from the
        # build env snapshot.
        env.unset("C_INCLUDE_PATH")
        env.unset("CPLUS_INCLUDE_PATH")
        env.unset("LIBRARY_PATH")

        # Keep the pkg-config discovery path for the basic-interface .pc as a
        # fallback discovery route (headers-only .pc relocated into
        # lib/pkgconfig by the lcmaps/1.6.7 recipe — see experience repo
        # build-system/lcmaps-1.6.7-pkgconfig-interface-consumption.md).
        env.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(lcmaps_pkg, "lib", "pkgconfig"),
        )

        # openldap: unconditional AC_CHECK_HEADER([ldap.h]) in configure and
        # liblcmaps_ldap_enf_la_LIBADD = -lldap in src/Makefile.am.
        incs = self._abs_dirs(self.dependencies["openldap"].cpp_info, "includedirs")
        if incs:
            env.append("CPPFLAGS", " ".join("-I%s" % d for d in incs))

        # Explicit link closure for every host dependency libdir: -L plus
        # -Wl,-rpath-link (build-chain-pitfalls rule; never rely on implicit
        # DT_NEEDED closure lookup over default search paths).
        seen = set()
        ldflags = []
        for _, dep in self.dependencies.host.items():
            if not getattr(dep, "package_folder", None):
                continue
            for d in self._abs_dirs(dep.cpp_info, "libdirs"):
                if d not in seen:
                    seen.add(d)
                    ldflags.append("-L%s" % d)
                    ldflags.append("-Wl,-rpath-link,%s" % d)
        if ldflags:
            env.append("LDFLAGS", " ".join(ldflags))

        # OHOS musl dlopen relocation scope adaptation (knowledge E004,
        # probed on device): a dlopen()ed DSO's undefined symbols resolve
        # ONLY against its own DT_NEEDED closure — NOT against the main
        # executable, its other startup libraries, or previously
        # dlopen()ed RTLD_GLOBAL objects. Upstream plugins carry undefined
        # lcmaps_* references resolved from the framework that dlopen()s
        # them (RTLD_NOW) — that model cannot relocate on this platform
        # (CI run5/run9 "Error relocating ...: lcmaps_log: symbol not
        # found" + minimal probes). POSIX capability-level fix: give every
        # plugin an explicit DT_NEEDED on the framework by linking with
        # -llcmaps_without_gsi (the framework is always loaded by the time
        # plugins are dlopen()ed, so the NEEDED is always satisfiable in
        # real use). Scoped with --as-needed so that non-plugin link
        # inputs (e.g. configure probes like AC_CHECK_LIB([dl]) conftests,
        # which never reference framework symbols and run without any
        # LD_LIBRARY_PATH) do not acquire a runtime framework dependency
        # (CI run10: "cannot run C compiled programs").
        env.append(
            "LDFLAGS",
            "-Wl,--as-needed -llcmaps_without_gsi -Wl,--no-as-needed",
        )

        tc.generate(env=env)

    def _remove_broken_libtool_wrappers(self):
        # libtool prefers .la wrappers over .so when resolving LIBADD=-lldap.
        # Dependency packages installed through conan's --prefix=/ + DESTDIR
        # scheme ship .la wrappers recorded with libdir='//lib' (e.g. openldap
        # libldap.la with dependency_libs '//lib/liblber.la'); libtool then
        # fails with "'//lib/liblber.la' is not a valid libtool archive"
        # (CI run3). Remove the broken wrappers so libtool links the real
        # .so — same remedy as the a52dec/0.7.4 recipe precedent (libtool
        # *.la wrappers removed from packages; conan itself never consumes
        # .la files).
        for _, dep in self.dependencies.host.items():
            if not getattr(dep, "package_folder", None):
                continue
            for libdir in self._abs_dirs(dep.cpp_info, "libdirs"):
                for la in glob.glob(os.path.join(libdir, "*.la")):
                    try:
                        with open(la, "r", encoding="utf-8", errors="ignore") as fh:
                            text = fh.read()
                    except OSError:
                        continue
                    if "//lib" in text:
                        self.output.info(
                            "Removing broken libtool wrapper: %s" % la
                        )
                        os.remove(la)

    def build(self):
        # Platform-only patches: config.guess/config.sub HarmonyOS recognition,
        # configure HMDFS tmpdir (E415-family), .mod symlink install fallback
        # (E018). No autoreconf (E089): the tarball ships a working configure.
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        self._remove_broken_libtool_wrappers()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # dlopen()ed modules only: no headers, no link interface, no .pc.
        # Consumers point the LCMAPS framework at <prefix>/lib/lcmaps.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
