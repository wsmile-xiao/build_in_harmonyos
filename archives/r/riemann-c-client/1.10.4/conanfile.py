#!/usr/bin/env python3
"""Conan recipe for riemann-c-client 1.10.4 (Autotools, C).

Riemann C client library (libriemann-client) plus the `riemann-client`
command-line tool for the Riemann monitoring system.

OHOS / CI adaptation notes (details in notes.md):

* protoc-c is unavailable on the OHOS build host and in CI (same situation as
  ocserv 1.5.0).  This package ships the pre-generated protobuf-c sources
  `lib/riemann/proto/riemann.pb-c.[ch]` (patches/0003, produced on this
  device with protoc 3.17.3 + protoc-gen-c built from protobuf-c 1.5.1), and
  patches configure.ac / Makefile.am (patches/0001, 0002) so the build copies
  those files instead of invoking protoc-c.
* The upstream source is a git archive: no `configure` script ships with it,
  so the Autotools files are bootstrapped after patching with conan
  tool_requires (libtoolize -> aclocal -> autoheader -> autoconf -> automake).
  PERL/PERL5LIB are pinned to the native OHOS perl the same way ding-libs
  0.7.0 does: conan's perl is ABI-incompatible with the automake scripts and
  breaks the bootstrap with Perl_my_cxt_init crashes (device-facts §一.23).
* `make check` runs the upstream Check suite (3 programs).  check_networked
  only registers its 15 cases when RCC_NETWORK_TESTS=1 AND a live Riemann
  server are available (upstream CI service container); without them the
  upstream program itself runs an empty suite.  The device run therefore
  executes the remaining upstream cases and records the networked ones as
  NOT_RUN with that reason in the PR statistics.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class RiemannCClientConan(ConanFile):
    name = "riemann-c-client"
    version = "1.10.4"
    description = "C client library and command-line tool for the Riemann monitoring system"
    license = "LGPL-3.0-or-later"
    homepage = "https://git.madhouse-project.org/algernon/riemann-c-client"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"riemann-c-client supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "riemann-c-client OHOS support is validated for armv8/AArch64"
            )

    def build_requirements(self):
        # The upstream tarball is a git archive (no configure/); regenerate the
        # Autotools files after applying the source patches so generated files
        # stay out of the patch set.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # pkg.m4 provides the PKG_PROG_PKG_CONFIG macro that configure.ac uses.
        self.tool_requires("pkgconf/3.0.6")
        # Upstream Check-based tests only; not part of the link interface.
        self.test_requires("check/0.15.2")

    def requirements(self):
        # W0 verified on the ohpcd registry (prebuilt OHOS armv8 binaries).
        # transitive_headers/libs: the *installed* public header
        # include/riemann/proto/riemann.pb-c.h does
        # `#include <protobuf-c/protobuf-c.h>`, so every consumer compiles
        # against protobuf-c headers and links the archive (et/7.0.0
        # precedent).
        self.requires(
            "protobuf-c/1.5.1", transitive_headers=True, transitive_libs=True
        )
        # TLS support (lib/riemann/client/tls.c) + the 2 TLS test registrations.
        self.requires("gnutls/3.8.10")
        # JSON output of the riemann-client CLI (upstream: optional at
        # configure time, enabled here so the shipped CLI keeps the feature).
        self.requires("json-c/0.18")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # check.pc / gnutls.pc / json-c.pc / libprotobuf-c.pc are all consumed
        # by configure's PKG_CHECK_MODULES probes (HAVE_CHECK, GNUTLS, JSON_C,
        # PROTOBUF_C).  Without them the probes fall back to "no" and the tests
        # / TLS / JSON features would be silently compiled out.
        PkgConfigDeps(self).generate()
        # Aggregates -I/-L of the whole host graph (gnutls's private nettle/
        # hogweed/gmp chain included) so the static CLI link does not underlink.
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # Build BOTH flavours: the upstream Check suite deliberately overrides
        # library symbols from the test objects (tests/mocks.c), which only
        # links cleanly against the shared object (the way upstream CI builds
        # it); the shipped package then keeps exactly one flavour per the
        # `shared` option and the CLI statically links our own archive
        # (patches/0005).
        tc.configure_args.extend(["--enable-shared", "--enable-static"])
        # riemann-c-client includes <json.h> bare (distro convention: json-c's
        # own .pc ships -I${includedir}/json-c).  The conan-regenerated
        # json-c.pc only carries ${includedir}, so inject the subdir.
        jsonc = self._dependency("json-c")
        if jsonc is not None:
            jsonc_include = os.path.join(jsonc.package_folder, "include", "json-c")
            if os.path.isdir(jsonc_include):
                tc.extra_cflags.append("-I{}".format(jsonc_include))
                self.output.info("extra include: bare <json.h> -> {}".format(jsonc_include))
        tc.generate()

    def _dependency(self, name):
        for dependencies in (
            self.dependencies.test,
            self.dependencies.host,
            self.dependencies.build,
        ):
            try:
                return dependencies[name]
            except KeyError:
                continue
        return None

    def _environment(self, for_tests=False):
        env = Environment()
        # PkgConfigDeps writes *.pc into the generators folder; keep the
        # profile's search path while putting generated metadata first.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        if str(self.settings.os) in ("Linux", "OHOS"):
            # The registry's gnutls/libgcrypt (and json-c) packages ship
            # *shared* objects — gnutls/libgcrypt even declare shared=False in
            # conaninfo yet package only .so files (verified by ls).  Every
            # linked ELF therefore needs the dependency lib dirs at load time:
            # configure's conftest, the `make check` programs, and the CLI.
            # The linker itself is unaffected (it uses -L from AutotoolsDeps).
            lib_dirs = []
            for dependencies in (self.dependencies.host, self.dependencies.test):
                for dep in dependencies.values():
                    libdir = os.path.join(dep.package_folder, "lib")
                    if os.path.isdir(libdir) and libdir not in lib_dirs:
                        lib_dirs.append(libdir)
            for libdir in reversed(lib_dirs):
                env.prepend_path("LD_LIBRARY_PATH", libdir)

        if str(self.settings.os) == "OHOS":
            # /tmp is read-only on the target; check(3) consults TEMP before
            # P_tmpdir, so spell out every common temp variable.
            tmp = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmp, exist_ok=True)
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            if for_tests:
                # Check's forked runner uses temp IPC files that are restricted
                # on HMDFS; in-process mode keeps every case (upstream's
                # AM_TESTS_ENVIRONMENT exports CK_FORK=no as well).
                env.define("CK_FORK", "no")
        return env

    def _bootstrap(self):
        """libtoolize -> aclocal -> autoheader -> autoconf -> automake.

        The conan Perl package is ABI-incompatible with the native OHOS Perl
        used by the Automake scripts.  Override both variables on every
        command: conan's aggregated build env otherwise restores the Perl
        package's incompatible PERL5LIB after a context manager exits
        (same workaround as ding-libs 0.7.0, device-facts §一.23).
        """
        automake = self._dependency("automake")
        automake_share = ""
        if automake is not None:
            automake_share = os.path.join(
                automake.package_folder, "share", "automake-1.18"
            )
        prefix = 'PERL="/data/service/hnp/bin/perl" PERL5LIB="%s" ' % automake_share
        for command in (
            "libtoolize --force --copy",
            "aclocal --force -I m4",
            "autoheader --force",
            "autoconf --force",
            "automake --add-missing --copy",
        ):
            self.run(prefix + command, cwd=self.source_folder, env="conanbuild")

    @property
    def _make_args(self):
        # Never let make re-run the maintainer tools: the recipe already ran
        # them after patching, and the workers' tool versions differ.
        return [
            "-j1",
            "ACLOCAL=true",
            "AUTOMAKE=true",
            "AUTOCONF=true",
            "AUTOHEADER=true",
        ]

    def _fix_dependency_la_files(self):
        """Repair `//lib` paths in dependency .la files (E236/E522, cattle-1.0
        and arm-none-eabi-gdb precedent).

        Several ohpcd binary packages were installed with prefix=/ so their
        libtool archives carry libdir='//lib' and dependency_libs entries like
        '//lib/libgpg-error.la'.  libtool resolves those when linking our
        static archive and dies with "'//lib/libgpg-error.la' is not a valid
        libtool archive".  Fix the metadata in place (consumer-side fix; the
        already-published registry recipes stay untouched), idempotent.
        """
        # Map every file in every dependency lib dir to the directory that
        # actually owns it (dependency_libs may point across packages).
        owners = {}
        dep_libdirs = []
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            dep_libdirs.append(libdir)
            for entry in os.listdir(libdir):
                owners.setdefault(entry, libdir)

        for libdir in dep_libdirs:
            for la_path in glob.glob(os.path.join(libdir, "*.la")):
                with open(la_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                new_content = content
                # libdir='//lib' -> this package's real lib directory
                new_content = new_content.replace(
                    "libdir='//lib'", "libdir='{}'".format(libdir)
                )
                # //lib/<file> -> the directory that owns <file>
                for entry, owner in owners.items():
                    new_content = new_content.replace(
                        "//lib/{}".format(entry), os.path.join(owner, entry)
                    )
                # remaining //-flavoured search paths
                new_content = new_content.replace("-L//lib", "-L{}".format(libdir))
                if new_content != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(new_content)
                    self.output.info("fixed la paths in {}".format(la_path))

    def build(self):
        apply_conandata_patches(self)
        # config.guess arrives via patch with mode 0644; some autoconf versions
        # exec it directly instead of through $SHELL.
        guess = os.path.join(self.source_folder, "config.guess")
        if os.path.isfile(guess):
            os.chmod(guess, 0o755)
            self.output.info("chmod +x: patched config.guess aux file")
        # E236: repair //lib paths in dependency .la files before libtool
        # resolves them at link time.
        self._fix_dependency_la_files()
        self._bootstrap()

        # HMDFS: once conan has created the build tree the parent directories
        # are no longer reachable through getcwd(), so the `pwd` probe Autoconf
        # runs before re-executing configure under CONFIG_SHELL=bash fails with
        # "working directory cannot be determined".  Publishing the logical
        # $PWD lets the shell resolve the directory without calling getcwd()
        # (same workaround as ding-libs / adms / aribb24 / aircrack).
        os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._environment().vars(self).apply():
            autotools.configure()
            autotools.make(args=self._make_args)

        # Full upstream Check suite, not a smoke subset (R51).
        with VirtualBuildEnv(self).vars().apply(), self._environment(for_tests=True).vars(self).apply():
            autotools.make(target="check", args=self._make_args)

    def package(self):
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._environment().vars(self).apply():
            autotools.install(args=self._make_args)

        # Libtool archives carry the build-time absolute libdir and are not
        # part of the Conan link interface.
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))
        # Both flavours were built (see generate()); ship only the one the
        # option declares, keeping the CLI (statically linked against our own
        # archive via patches/0005) self-contained either way.
        if self.options.shared:
            rm(self, "*.a", folder=os.path.join(self.package_folder, "lib"))
            self.output.info("package flavour: shared (static archive removed)")
        else:
            rm(self, "libriemann-client.so*", folder=os.path.join(self.package_folder, "lib"))
            self.output.info("package flavour: static (shared objects removed)")
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.GPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        # Install-tree reality check (stop-loss precedent 9: rc=0 must be
        # confirmed against installed artefacts — a broken install-sh silently
        # shipped 1/24 headers elsewhere).
        expected = [
            "include/riemann/client.h",
            "include/riemann/event.h",
            "include/riemann/message.h",
            "include/riemann/attribute.h",
            "include/riemann/query.h",
            "include/riemann/simple.h",
            "include/riemann/riemann-client.h",
            "include/riemann/proto/riemann.pb-c.h",
            "lib/pkgconfig/riemann-client.pc",
            "bin/riemann-client",
        ]
        if self.options.shared:
            expected.append("lib/libriemann-client.so")
        else:
            expected.append("lib/libriemann-client.a")
        missing = [
            path
            for path in expected
            if not os.path.exists(os.path.join(self.package_folder, path))
        ]
        if missing:
            raise ConanException(
                "install tree incomplete, missing: {}".format(", ".join(missing))
            )
        self.output.info(
            "install_tree_check: {}/{} expected files present".format(
                len(expected), len(expected)
            )
        )

    def package_info(self):
        self.cpp_info.libs = ["riemann-client"]
        # The package ships bin/riemann-client; keep bindirs explicit so the
        # recipe self-declares as a CLI-capable package (PF8 reads this
        # literal; the default is the same ["bin"]).
        self.cpp_info.bindirs = ["bin"]
        # The package ships the upstream lib/riemann/riemann-client.pc.
        self.cpp_info.set_property("pkg_config_name", "riemann-client")
        self.cpp_info.set_property("cmake_file_name", "riemann-c-client")
        self.cpp_info.set_property("cmake_target_name", "riemann-c-client::riemann-client")

        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
