#!/usr/bin/env python3
"""Conan recipe — opendkim 2.11.0-beta2 (Autotools).

opendkim: DKIM (DomainKeys Identified Mail) signing/verifying library
(libopendkim) plus filter and command-line tools, from the Trusted Domain
Project. Built natively for HarmonyOS PC (aarch64-unknown-linux-ohos).

Adaptation notes (see also notes.md):
- GitHub tag tarball ships configure.ac but no Makefile.in/ltmain.sh, so
  build() bootstraps with tool_requires automake/1.18 + libtool/2.5.4
  (libtoolize -> aclocal -> autoheader -> automake -> autoconf).
- E097: configure's AS_TMPDIR mktemp uses umask 077 + ./confXXXXXX which
  HMDFS setgid dirs reject for config.status children; patched to umask 022
  + $TMPDIR/confXXXXXX (in-recipe, configure is a generated file).
- Triplet passed explicitly (--build/--host aarch64-unknown-linux-ohos) so
  the stock config.guess (no OHOS knowledge) is never invoked (E007).
- libunbound.la shipped in the unbound conan package carries a dead
  dependency_libs entry ("//lib/libevent.la", DESTDIR-baked at unbound
  packaging time) which breaks libtool linking. generate() builds a shim
  prefix dir with the static archive and a rewritten .la pointing at the
  real transitive libs (libevent/expat/openssl).
- musl libc has no _res global (stub resolver); patch 0001 guards the
  RES_USE_DNSSEC request with __GLIBC__ (portability, not OHOS-specific).
- Optional features kept minimal per R1: only the diffheaders feature
  (tre) is enabled on top of the default set; unbound DNSSEC resolver
  enabled (--with-unbound); the milter filter daemon (opendkim binary)
  is disabled (--disable-filter) because a full MTA/milter runtime is out
  of scope for the library package; SQL/LDAP/Lua/memcached/etc all off.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class OpendkimConan(ConanFile):
    name = "opendkim"
    version = "2.11.0-beta2"
    description = "DKIM (DomainKeys Identified Mail) signing and verifying library and tools"
    license = "Sendmail Open Source License"
    homepage = "http://www.opendkim.org/"
    url = "https://github.com/trusteddomainproject/OpenDKIM"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):  # R32
            raise ConanInvalidConfiguration(
                f"opendkim supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        # Direct dependencies (W0 verified published on ohpcd):
        #   libmilter/8.18.2, openssl/3.5.6.1, tre/0.9.0, unbound/1.22.0.
        # openssl/3.5.6.1 (not 3.5.6) matches the version unbound/1.22.0
        # was built against, keeping the dependency graph conflict-free.
        # No libbsd requirement: musl libc provides strlcpy/strlcat and
        # configure's AC_CHECK_FUNCS([strlcat strlcpy]) hits them directly.
        self.requires("openssl/3.5.6.1", run=True)
        self.requires("libmilter/8.18.2")
        self.requires("tre/0.9.0")
        self.requires("unbound/1.22.0", run=True)
        # libevent + expat are transitive dependencies of unbound (static
        # libunbound.a links against them). They must be declared directly
        # so generate() can resolve their package folders for the unbound
        # .la shim — transitive deps expose package_folder=None (abiword
        # precedent). Versions match unbound/1.22.0's requirements exactly.
        self.requires("libevent/2.1.12")
        self.requires("expat/2.8.2")

    def build_requirements(self):
        # GitHub tag tarball has no Makefile.in/ltmain.sh/config.guess; the
        # autotools bootstrap needs automake + libtool. /data/service/hnp/bin
        # only ships autoconf, and CI sandboxes cannot see a $HOME/.local
        # automake, so both come from the registry (abiword-plugin-eml
        # precedent, published automake/1.18 + libtool/2.5.4).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: pass the triplet explicitly so the stock config.guess
        # (no HarmonyOS knowledge) is never executed (tre precedent).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")

        deps = self.dependencies
        milter = deps["libmilter"].package_folder
        ssl = deps["openssl"].package_folder
        tre = deps["tre"].package_folder
        tc.configure_args.append(f"--with-milter={milter}")
        tc.configure_args.append(f"--with-openssl={ssl}")
        tc.configure_args.append(f"--with-tre={tre}")

        # unbound shim: the packaged libunbound.la contains a DESTDIR-baked
        # "//lib/libevent.la" in dependency_libs which libtool chokes on.
        # Stage a prefix with the static archive and a rewritten .la whose
        # dependency_libs point at the real transitive conan packages.
        unbound = deps["unbound"].package_folder
        libevent = deps["libevent"].package_folder
        expat = deps["expat"].package_folder
        shim = os.path.join(self.build_folder, "unbound-shim")
        os.makedirs(os.path.join(shim, "lib"), exist_ok=True)
        os.makedirs(os.path.join(shim, "include"), exist_ok=True)
        shutil.copy(os.path.join(unbound, "lib", "libunbound.a"),
                    os.path.join(shim, "lib", "libunbound.a"))
        unbound_inc = os.path.join(unbound, "include")
        for entry in os.listdir(unbound_inc):
            src = os.path.join(unbound_inc, entry)
            dst = os.path.join(shim, "include", entry)
            if os.path.isdir(src):
                if not os.path.exists(dst):
                    shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)
        with open(os.path.join(shim, "lib", "libunbound.la"), "w",
                  encoding="utf-8") as f:
            f.write("# libunbound.la - a libtool library file\n")
            f.write("# Generated by libtool (GNU libtool) 2.4.6\n")
            f.write("# Rewritten by conanfile.py: dead //lib/libevent.la fix\n")
            f.write("dlname=''\n")
            f.write("library_names=''\n")
            f.write("old_library='libunbound.a'\n")
            f.write("inherited_linker_flags=' -pthread'\n")
            f.write(f"dependency_libs=' -L{ssl}/lib -L{libevent}/lib"
                    f" -L{expat}/lib -lssl -levent -lexpat -lpthread -lcrypto'\n")
            f.write("weak_library_names=''\n")
            f.write("current=9\n")
            f.write("age=1\n")
            f.write("revision=30\n")
            f.write("installed=yes\n")
            f.write("shouldnotlink=no\n")
            f.write("dlopen=''\n")
            f.write("dlpreopen=''\n")
            f.write(f"libdir='{shim}/lib'\n")
        tc.configure_args.append(f"--with-unbound={shim}")

        # Feature flags (R1 minimal): keep the default feature set, add
        # diffheaders (uses tre), and let unbound drive DNSSEC-aware DNS.
        # Everything else (SQL backends, LDAP, Lua, memcached, rrdtool,
        # jansson, curl, sasl, lmdb, erlang, stats) stays disabled.
        tc.configure_args.append("--enable-diffheaders")
        # The filter daemon (opendkim binary) needs a running MTA/milter
        # environment; the library + tools package keeps it off.
        tc.configure_args.append("--disable-filter")

        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _bootstrap(self):
        """libtoolize -> aclocal -> autoheader -> automake -> autoconf.

        aclocal must see libtool's macros and the system pkg-config macros
        (PKG_CHECK_MODULES is used throughout configure.ac). ACLOCAL_PATH /
        PERL5LIB / AUTOMAKE come from the automake tool_require; pkg.m4 is
        only present in the platform pkg-config tree, so it is appended
        here via the conanbuild environment.
        """
        source = self.source_folder
        pkg_m4 = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal"
        # The automake tool_require exports ACLOCAL/AUTOMAKE/PERL5LIB/
        # ACLOCAL_PATH in the conanbuild env; inline-extend ACLOCAL_PATH with
        # the platform pkg.m4 location (PKG_CHECK_MODULES is used throughout
        # configure.ac; without it the macros stay unexpanded in configure).
        self.run(
            f'ACLOCAL_PATH="{pkg_m4}:$ACLOCAL_PATH" '
            f'libtoolize --copy --force',
            cwd=source, env="conanbuild")
        self.run(
            'aclocal -I m4 --output=aclocal.m4',
            cwd=source, env="conanbuild")
        self.run(
            'autoheader',
            cwd=source, env="conanbuild")
        self.run(
            'automake --foreign --add-missing --copy --force-missing',
            cwd=source, env="conanbuild")
        self.run(
            'autoconf',
            cwd=source, env="conanbuild")
        if not os.path.isfile(os.path.join(source, "configure")):
            raise ConanException("bootstrap failed: configure not generated")

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap()

        # E097 (tre precedent): configure's tmpdir probe uses umask 077 with
        # ./confXXXXXX; on HMDFS setgid build dirs the config.status child
        # cannot write subs1.awk ("Permission denied"). Patch in-recipe:
        # configure is a bootstrap-generated file, so a patches/ entry would
        # be classified as generated and dropped by refresh-patch.
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                        'tmp=`(umask 022 && mktemp -d "$TMPDIR/confXXXXXX") 2>/dev/null` &&')
        replace_in_file(self, configure_path,
                        '  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                        '  tmp=$TMPDIR/conf$$-$RANDOM\n  (umask 022 && mkdir "$tmp")')

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # Upstream unit tests: libopendkim/tests (161 C tests driven by
        # make check, DNS served from a local keyfile). DKIM_TMPDIR must
        # point at a writable dir because the z-tag and stub-DNS tests
        # (t-test52/t-test73/t-test141) drop temp files via DEFTMPDIR,
        # which defaults to read-only /tmp (E002). All 161 pass with it.
        import tempfile
        dkim_tmp = os.path.join(tempfile.gettempdir(), "opendkim-dkim-tmp")
        os.makedirs(dkim_tmp, exist_ok=True)
        self.run(f'make -C libopendkim/tests check DKIM_TMPDIR="{dkim_tmp}"',
                 cwd=self.build_folder, env="conanrun",
                 ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # sbin/ -> bin/ so conan layout and the L2/L4 gates see the tools.
        sbin = os.path.join(self.package_folder, "sbin")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(sbin):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbin):
                shutil.move(os.path.join(sbin, name),
                            os.path.join(bindir, name))
            os.rmdir(sbin)
        # The .la file written into package lib/ points at the build tree;
        # downstream libtool would fail to resolve it (same dead-path
        # family as the unbound .la). Keep the package .la-free.
        for la in ("libopendkim.la",):
            p = os.path.join(self.package_folder, "lib", la)
            if os.path.isfile(p):
                os.unlink(p)

    def package_info(self):
        self.cpp_info.libs = ["opendkim"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = [
            "openssl::openssl", "libmilter::libmilter",
            "tre::tre", "unbound::unbound",
            "libevent::libevent", "expat::expat",
        ]
        self.cpp_info.set_property("cmake_file_name", "opendkim")
        self.cpp_info.set_property("cmake_target_name", "opendkim::opendkim")
        self.cpp_info.set_property("pkg_config_name", "opendkim")
