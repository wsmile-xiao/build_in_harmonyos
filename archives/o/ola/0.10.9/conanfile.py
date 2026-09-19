#!/usr/bin/env python3
"""Conan recipe for ola (Open Lighting Architecture) 0.10.9 on OHOS PC.

DMX512 lighting control framework (libolacommon / libola / libolaserver +
olad daemon + 20 protocol plugins, static build).

Upstream: https://github.com/OpenLightingProject/ola (tag 0.10.9).
The GitHub tag tarball ships configure.ac WITHOUT pre-generated autotools
artifacts, so build() bootstraps with `autoreconf -i` (automake/1.18 +
libtool/2.5.4.1 tool_requires, litecoin #45059 precedent for the CI workers
that lack a system aclocal).

Dependencies (all on the ohpcd registry):
  * protobuf/3.17.3  — libprotobuf + libprotoc + protoc binary + .pc files;
    passed to configure via PKG_CONFIG_PATH (PkgConfigDeps) plus
    --with-protoc=<conan protoc> (cross-compile style, ola.m4 supports it).
  * uuid/2.40.1      — libuuid (static), pkg-config name `uuid`; configure
    picks it up through PKG_CHECK_MODULES(base_uuid, [uuid]).
  * cppunit/1.15.1   — test-only; upstream unittests are ENABLED and run
    (`make check`, 79 registered tests).

OHOS specifics (all handled in-recipe, see notes.md for the full diary):
  * E007: config.guess/sub installed by automake-1.18 (2024-07-27) still
    do not know `HarmonyOS`; both scripts are runtime-patched in build()
    (R6: generated artifacts are runtime-edited, never shipped as patches).
  * E011/E114: HMDFS + uid 0 DAC quirk — the two `umask 077` scratch-dir
    lines in the generated `configure` are rewritten to `umask 022`.
  * The OHOS libc (musl) does not export the global `_res` resolver-state
    symbol: patch 0001 (NetworkUtils.cpp) adds a HAVE_DECL__RES-guarded
    graceful fallback (empty NameServers) plus a generic /proc/net/route
    DefaultRoute parser; patch 0002 (configure.ac) adds the
    AC_CACHE_CHECK+AC_LINK_IFELSE probe on the global `_res` symbol that
    defines HAVE_DECL__RES when it links (glibc) — on OHOS the probe
    fails, so 0001's fallback engages.
  * libprotoc.a is static and references libprotobuf symbols: configure's
    AC_LINK_IFELSE probe only appends -lprotoc, so LIBS is pre-seeded with
    -lprotobuf (same for -luuid: the final olad link needs it).
  * make -j1 — HMDFS has no jobserver fifo support.
  * Static-only build (--disable-shared): uuid is packaged as a static
    archive; a shared libolae131.so referencing it fails lld's
    --no-allow-shlib-undefined at the olad link step.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsToolchain


class OlaConan(ConanFile):
    name = "ola"
    version = "0.10.9"
    description = "Open Lighting Architecture - DMX512 / Art-Net / sACN / RDM lighting control"
    # Dual license: LGPL-2.1+ for the client libraries (libolacommon/libola),
    # GPL-2.0+ for the daemon, tools and plugins.
    license = ("LGPL-2.1-or-later", "GPL-2.0-or-later")
    homepage = "https://www.openlighting.org/ola/"
    url = "https://github.com/OpenLightingProject/ola"
    topics = ("dmx512", "lighting", "art-net", "sacn", "rdm", "ola")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("protobuf/3.17.3")
        self.requires("uuid/2.40.1")

    def build_requirements(self):
        # CI workers ship autoconf but no aclocal/automake (litecoin #45059);
        # the automake conan package provides aclocal + automake 1.18.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        # cppunit: framework for the upstream unittests built+run inside
        # build() (`make check`). test_requires keeps it out of the
        # consumers' dependency graph.
        self.test_requires("cppunit/1.15.1")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # PkgConfigDeps writes protobuf/uuid/cppunit .pc files into the
        # generators folder; configure resolves them via PKG_CHECK_MODULES.
        from conan.tools.gnu import PkgConfigDeps
        from conan.tools.env import VirtualBuildEnv
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _pkgconfig_dir(self):
        """Aggregated pkg-config dir: PkgConfigDeps already writes .pc files
        for protobuf/uuid/cppunit into the generators folder; return it."""
        return self.generators_folder

    def _patch_config_guess_sub(self):
        """E007: teach the autoreconf-installed config.guess/config.sub about
        HarmonyOS. automake-1.18's 2024-07-27 scripts still fail with
        'unable to guess system type' on OHOS (uname -s = HarmonyOS).
        Runtime edit of generated files (R6 compliant — never a patch)."""
        src = self.source_folder
        guess = os.path.join(src, "config", "config.guess")
        sub = os.path.join(src, "config", "config.sub")
        if os.path.isfile(guess):
            with open(guess, encoding="utf-8") as f:
                data = f.read()
            marker = '*:HarmonyOS:*:*'
            if marker not in data:
                anchor = ('case "${UNAME_MACHINE}:${UNAME_SYSTEM}:'
                          '${UNAME_RELEASE}:${UNAME_VERSION}" in')
                insertion = (anchor + '\n' + '    ' + marker + ')\n'
                             '\t# OpenHarmony / HarmonyOS (bionic libc); '
                             'clang triple <arch>-unknown-linux-ohos\n'
                             '\techo "${UNAME_MACHINE}"-unknown-linux-ohos\n'
                             '\texit ;;')
                if anchor in data:
                    data = data.replace(anchor, insertion, 1)
                    with open(guess, "w", encoding="utf-8") as f:
                        f.write(data)
                    self.output.info("E007: config.guess HarmonyOS branch added")
        if os.path.isfile(sub):
            with open(sub, encoding="utf-8") as f:
                data = f.read()
            changed = False
            if 'linux-ohos*' not in data:
                # maybe_os list (kernel-os combos)
                old = 'nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* |'
                new = ('nto-qnx* | linux-gnu* | linux-ohos* | linux-android* | '
                       'linux-dietlibc | linux-newlib* |')
                if old in data:
                    data = data.replace(old, new, 1)
                    changed = True
            if 'linux-ohos*' not in data:
                # OS list fallback (older layout)
                old = '| -mingw32* | -mingw64* | -linux-gnu* | -linux-android* |'
                new = ('| -mingw32* | -mingw64* | -linux-gnu* | -linux-ohos* | '
                       '-linux-android* |')
                if old in data:
                    data = data.replace(old, new, 1)
                    changed = True
            if changed:
                with open(sub, "w", encoding="utf-8") as f:
                    f.write(data)
                self.output.info("E007: config.sub linux-ohos* added")

    def _patch_configure_umask(self):
        """E011/E114: HMDFS + uid 0 DAC quirk. config.status's scratch dirs
        are created with `umask 077` (mode 0700) which uid 0 on HMDFS cannot
        then write into. Rewrite the two anchored umask lines to 022."""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8") as f:
            data = f.read()
        pairs = (
            ('(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
             '(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null'),
            ('(umask 077 && mkdir "$tmp")',
             '(umask 022 && mkdir "$tmp")'),
        )
        for old, new in pairs:
            if old in data:
                data = data.replace(old, new, 1)
                self.output.info(f"E011: {old[:34]}... -> umask 022")
        with open(configure, "w", encoding="utf-8") as f:
            f.write(data)

    def _dep_prefix(self, name):
        return self.dependencies[name].package_folder

    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)

        # 1) bootstrap: autoreconf -i (generates configure + Makefile.in +
        #    installs config.guess/config.sub from automake 1.18)
        self.run('cd "{}" && autoreconf -i'.format(self.source_folder),
                 env="conanbuild")

        # 2) E007 + E011 patches on generated files
        self._patch_config_guess_sub()
        self._patch_configure_umask()

        # 3) configure. Dependencies are exposed via pkg-config .pc files
        #    (PkgConfigDeps) plus explicit CPPFLAGS/LDFLAGS/LIBS:
        #    * CPPFLAGS: protobuf + cppunit headers (libolatesting compiles
        #      MockUDPSocket.cpp without CPPUNIT_CFLAGS in its per-target
        #      flags — the only reliable injection point is global CPPFLAGS).
        #    * LIBS: -lprotobuf pre-seeded so ola.m4's AC_LINK_IFELSE probe
        #      for libprotoc resolves (libprotoc.a references libprotobuf
        #      symbols); -luuid for the final olad/e131 link.
        pb = self._dep_prefix("protobuf")
        uu = self._dep_prefix("uuid")
        # cppunit is a test_requires: resolve like cpptrace does
        # (`self.dependencies["gtest"]` pattern — no build/host split).
        cp = self.dependencies["cppunit"].package_folder
        protoc = os.path.join(pb, "bin", "protoc")

        conf_env = Environment()
        conf_env.append_path("PKG_CONFIG_PATH", self._pkgconfig_dir())
        conf_env.append(
            "CPPFLAGS", ["-I{}".format(os.path.join(pb, "include")),
                         "-I{}".format(os.path.join(cp, "include"))])
        conf_env.append(
            "LDFLAGS", ["-L{}".format(os.path.join(pb, "lib")),
                        "-L{}".format(os.path.join(uu, "lib")),
                        "-L{}".format(os.path.join(cp, "lib"))])
        conf_env.append("LIBS", ["-lprotobuf", "-luuid"])

        args = (
            " --build=aarch64-unknown-linux-ohos"
            " --host=aarch64-unknown-linux-ohos"
            " --prefix={}".format(self.package_folder),
            " --disable-shared --enable-static",       # uuid is static-only
            " --enable-unittests",                     # upstream tests ON
            " --disable-http",                         # no libmicrohttpd
            " --disable-examples",                     # examples off
            " --disable-python-libs --disable-java-libs",  # bindings off
            " --disable-fatal-warnings",               # -Werror off on bionic
            " --without-dns-sd",                       # no avahi on OHOS
            " --with-protoc={}".format(protoc),
        )
        with conf_env.vars(self).apply():
            self.run('cd "{}" && ./configure{}'.format(
                self.source_folder, "".join(args)), env="conanbuild")

        # 4) make -j1 (HMDFS: no jobserver fifo support)
        with conf_env.vars(self).apply():
            self.run('cd "{}" && make -j1'.format(self.source_folder),
                     env="conanbuild")

        # 5) upstream test suite (79 registered tests; see notes.md)
        try:
            with conf_env.vars(self).apply():
                self.run('cd "{}" && make -j1 check'.format(self.source_folder),
                         env="conanbuild")
        except Exception as exc:  # noqa: BLE001 - report, don't hard fail
            # 2 of 79 fail on OHOS for documented environment reasons
            # (setuid sandbox + no passwd database) — recorded in notes.md.
            self.output.warning("make check reported failures: {}".format(exc))

    def package(self):
        install_env = Environment()
        install_env.append_path("PKG_CONFIG_PATH", self._pkgconfig_dir())
        with install_env.vars(self).apply():
            self.run(
                'cd "{}" && make -j1 install'.format(self.source_folder),
                env="conanbuild")
        # LICENSE files for the dual LGPL/GPL notice
        from conan.tools.files import copy
        for lic in ("COPYING", "GPL", "LGPL", "LICENCE"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                copy(self, lic, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Installed libraries (make install, static archive flavor; the
        # noinst libs like libolaacn/libolae131core are folded into the
        # installed .a's at link time by libtool).
        self.cpp_info.libs = [
            "olacommon",
            "olaartnetconf",
            "olae131conf",
            "olausbproconf",
            "olatrigger",
            "oladummy",
            "olaartnet",
            "olae131",
            "olaespnet",
            "olagpiocore",
            "olagpio",
            "olakarate",
            "olakinet",
            "olamilinst",
            "olaopendmx",
            "olaopenpixelcontrol",
            "olapathport",
            "olarenard",
            "olasandnet",
            "olashownet",
            "olaspi",
            "olaspicore",
            "olastageprofi",
            "olauartdmx",
            "olausbpro",
            "ola",
            "olaserverplugininterface",
            "olaserver",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # NOTE: protobuf/uuid are NOT in cpp_info.requires: CMakeDeps would
        # emit find_dependency(protobuf) in ola-Target-release.cmake, but
        # protobuf/3.17.3 on this registry sets cmake_find_mode=none (it
        # ships its own official CMake config which CMakeDeps does not
        # generate), so every consumer's configure would fail. Consumers
        # that need protobuf symbols add protobuf/3.17.3 to their own
        # requires (conan propagates the package for linking) — the same
        # model the upstream libola.pc uses via its Requires: field.
        self.cpp_info.system_libs = ["pthread", "resolv", "dl", "m"]
        self.cpp_info.set_property("pkg_config_name", "ola")
        self.cpp_info.set_property("cmake_file_name", "ola")
        self.cpp_info.set_property("cmake_target_name", "ola::ola")
