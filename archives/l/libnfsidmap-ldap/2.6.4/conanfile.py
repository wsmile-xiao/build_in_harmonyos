#!/usr/bin/env python3
"""Conan recipe — libnfsidmap-ldap 2.6.4.

libnfsidmap is the NFSv4 ID-mapping library (user/group name <-> uid/gid).
Upstream merged it into the nfs-utils source tree as ``support/nfsidmap/``, so
version 2.6.4 is the nfs-utils version and the source is the official nfs-utils
release tarball.  The ``-ldap`` suffix denotes the LDAP mapping plugin
(``umich_ldap.so``) that gives this package its identity.

Shipped artifacts (only ``support/nfsidmap`` and its ``libnfsconf`` helper are
built -- the rest of nfs-utils, e.g. nfsd/mountd/gssd, is out of scope):

  lib/libnfsidmap.so.1.0.0 (+ .so, .so.1 symlinks, libnfsidmap.a)
  lib/libnfsidmap/{nsswitch,static,regex,umich_ldap}.so   (dlopen()ed plugins)
  include/nfsidmap.h, include/nfsidmap_plugin.h
  lib/pkgconfig/libnfsidmap.pc
  share/man/man3/nfs4_uid_to_name.3, share/man/man5/idmapd.conf.5

Dependencies (all published in the ohpcd repository, see notes.md for the
``conan download`` evidence):

  * openldap   -- ``ldap.h`` + ``-lldap``: the LDAP mapping plugin itself.
  * krb5       -- ``--enable-gss`` default path, and ``-lgssapi_krb5`` for the
                  LDAP SASL interactive-bind branch.
  * cyrus-sasl -- ``sasl_interact_t`` from ``sasl/sasl.h`` enables
                  ENABLE_LDAP_SASL in umich_ldap.c.
  * libevent, uuid, libtirpc, sqlite3 -- unconditional gates of the nfs-utils
    top level configure (AC_LIBEVENT, uuid/uuid.h, rpc/rpc.h + pkg-config,
    AC_SQLITE3_VERS for nfsdcld).  None of them is linked by the shipped
    artifacts.

OHOS platform adaptations (see notes.md for commands, logs and evidence):

  * ``config.guess``/``config.sub`` carry the ``aarch64-unknown-linux-ohos``
    triplet (E007/E122) instead of passing --build/--host, which would make
    configure misdetect a cross build and skip every run test.
  * ``configure``: the tree-wide hard gate requiring getrpcbynumber(_r) is
    downgraded to a warning.  Neither OHOS musl nor libtirpc provides the
    symbol and its only user (support/nfs/svc_socket.c, part of libnfs.la) is
    outside this package's build scope.
  * ``configure``: the config.status temporary directory is created with a
    ``$$``-based name under umask 000 -- HMDFS makes a mktemp-created 0700
    directory unwritable for the build user (E110/E112/E118; the cln/1.3.7
    fix, CI-proven).
  * ``support/nfs/conffile.c``: weak definitions of versionsort() and
    strverscmp(), absent from musl-based libcs (E534 technique, GNU algorithm).
    conf_init_dir() calls versionsort() unconditionally, so the file cannot be
    compiled without them.
  * ``--with-krb5=<krb5 package folder>``: aclocal/kerberos5.m4 only looks for
    ``krb5-config`` in fixed system directories, never in the Conan cache.
  * ``--disable-nfsv41 --disable-uuid --disable-nfsrahead``: libdevmapper,
    libblkid and libmount.pc are not published in the repository; the switches
    only affect nfsd/blkmapd/nfsrahead, none of which is built here.
    ``--enable-ldap`` is passed on purpose so that a missing LDAP stack fails
    loudly instead of silently dropping the plugin.
  * ``support/nfsidmap/Makefile.am``/``Makefile.in``: each plugin records a
    DT_NEEDED on libnfsidmap.so.1.  Upstream expects the *host* process to
    provide the symbols the plugins reference (nfsidmap_conf_path,
    nfsidmap_config_get, nfs4_get_default_domain), which only works on loaders
    that expose the host's global symbol scope to dlopen()ed objects; on
    HarmonyOS a plugin resolves symbols exclusively from its own DT_NEEDED
    closure, so without this change no plugin can ever be loaded.  On glibc
    the library is already loaded when a plugin is opened, so the extra
    DT_NEEDED binds to the same instance and stays inert.
  * The build is done in-tree: the upstream ``support/*`` Makefiles have no
    ``-I$(top_srcdir)/support/include`` and therefore do not support VPATH
    builds (``conffile.h`` is not found).
  * ``*.la`` files of the dependencies are removed before the build: the
    published openldap package ships ``libldap.la`` with ``libdir='//lib'`` and
    ``dependency_libs='... //lib/liblber.la'``, which aborts libtool with
    "was moved" / "is not a valid libtool archive".
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Environment for every configure/make invocation:
#   CONFIG_SHELL/SHELL=/bin/sh -- the OHOS bash injected through the profile's
#     [buildenv] fails getcwd() on HMDFS directories (DRAFT-6487), which breaks
#     autoconf's internal config.guess/config.sub/config.status calls.
#   ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER=true -- HMDFS timestamp granularity
#     lets make believe the autotools files are stale and re-run
#     "config.status --recheck" (i.e. configure again) inside the build; the
#     shipped Makefile.in are valid, so regeneration is neutralized
#     (libmirage / dbus-glib precedent).
BUILD_ENV = ("CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
             "ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true")

CONFIGURE_ARGS = [
    # Enabled explicitly: this package *is* the LDAP plugin, so a missing LDAP
    # stack must fail the configure step instead of silently skipping it.
    "--enable-ldap",
    # No system rpcgen on OHOS; nfs-utils ships its own (tools/rpcgen).
    "--with-rpcgen=internal",
    # Libraries of these gates are not published and the switches only affect
    # components outside this package: libdevmapper (nfsv41/blkmapd),
    # libblkid (uuid), libmount.pc (nfsrahead).
    "--disable-nfsv41",
    "--disable-uuid",
    "--disable-nfsrahead",
]


class LibNfsidmapLdapConan(ConanFile):
    name = "libnfsidmap-ldap"
    version = "2.6.4"
    description = ("NFSv4 ID-mapping library (libnfsidmap) with the LDAP "
                   "mapping plugin umich_ldap, built from the nfs-utils tree")
    license = "BSD-2-Clause"
    homepage = "https://linux-nfs.org/"
    url = ""  # CI fills this

    # A shared-library package: libnfsidmap.so.1 plus the dlopen()ed mapping
    # plugins.  Upstream's default (static + shared) is kept, so the static
    # libnfsidmap.a is shipped as well; the plugins however only make sense as
    # shared modules, i.e. a static-only configuration is not supported.
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Plugin payload: -lldap and (SASL branch) -lgssapi_krb5.
        self.requires("openldap/2.6.7")
        self.requires("krb5/1.22.1")
        # ENABLE_LDAP_SASL probe (sasl_interact_t from sasl/sasl.h).
        self.requires("cyrus-sasl/2.1.28")
        # Unconditional gates of the nfs-utils top level configure.
        self.requires("libevent/2.1.13")
        self.requires("uuid/2.40.1")
        self.requires("libtirpc/1.3.7")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _dependency_flags(self):
        """Include/library search paths of every dependency, for configure.

        AutotoolsToolchain does not add them on its own (the autotools flow
        normally relies on pkg-config/AutotoolsDeps), but nfs-utils probes its
        dependencies with AC_CHECK_HEADER/AC_CHECK_LIB.
        """
        cflags, ldflags = [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                # transitive dependencies whose binary is not needed here
                continue
            components = dep.cpp_info.aggregated_components()
            cflags.extend("-I" + inc for inc in components.includedirs)
            ldflags.extend("-L" + lib for lib in components.libdirs)
        return cflags, ldflags

    def _configure_args(self):
        # aclocal/kerberos5.m4 searches only fixed system directories for
        # krb5-config, so point it at the Conan package explicitly.
        return CONFIGURE_ARGS + [
            "--with-krb5=" + self.dependencies["krb5"].package_folder,
        ]

    def _drop_dependency_la_files(self):
        """Remove the dependency libtool archives before linking.

        The published openldap package ships libldap.la with libdir='//lib' and
        dependency_libs='... //lib/liblber.la'; libtool aborts on it with
        "was moved" / "is not a valid libtool archive".  Conan publishes the
        link information through cpp_info and the .pc files, so the archives
        are not needed (bookloupe / cyrus-sasl precedent).
        """
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            pattern = os.path.join(dep.package_folder, "lib", "**", "*.la")
            for la in glob.glob(pattern, recursive=True):
                try:
                    os.remove(la)
                    self.output.info("removed dependency .la: " + la)
                except OSError:
                    pass

    def generate(self):
        tc = AutotoolsToolchain(self)
        cflags, ldflags = self._dependency_flags()
        tc.extra_cflags = cflags
        tc.extra_ldflags = ldflags
        tc.generate()
        PkgConfigDeps(self).generate()

    def _restore_autotools_script_modes(self):
        """Restore the executable bit of the shipped autotools helpers (E490).

        The helper scripts are executable inside the tarball and in the local
        Conan build folder (verified 0770), but certain HarmonyOS staging paths
        preserve source content while dropping the mode, and configure() is
        invoked directly -- a lost bit would fail the build with EACCES.
        """
        for helper in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "compile", "depcomp", "ltmain.sh"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass

    def build(self):
        self._drop_dependency_la_files()
        self._restore_autotools_script_modes()
        src = self.source_folder
        args = " ".join(self._configure_args())
        # In-tree build: the upstream support/* Makefiles do not support VPATH
        # builds (they lack -I$(top_srcdir)/support/include, so conffile.h is
        # not found).  cd is done inside the shell on purpose (DRAFT-6487).
        self.run(f'cd "{src}" && {BUILD_ENV} ./configure '
                 f'--prefix="{self.package_folder}" {args}', env="conanbuild")
        self.run(f'cd "{src}" && {BUILD_ENV} make -C support/nfs libnfsconf.la',
                 env="conanbuild")
        self.run(f'cd "{src}" && {BUILD_ENV} make -C support/nfsidmap',
                 env="conanbuild")
        # Upstream ships no automated test suite for support/nfsidmap (proved
        # by grep over the Makefile.am files, see notes.md / MANIFEST.yml), so
        # `make check` is expected to be a no-op; it is still run so that the
        # absence is visible in the build log.  The only upstream test entry
        # point is the manual libtest.c, exercised by test_package.
        self.run(f'cd "{src}" && {BUILD_ENV} make -C support/nfsidmap check',
                 env="conanbuild")

    def package(self):
        src = self.source_folder
        self.run(f'cd "{src}" && {BUILD_ENV} make -C support/nfsidmap install',
                 env="conanbuild")
        # Drop the libtool archives we produced: they record the build-time
        # package_folder, and the link information is already published through
        # cpp_info and libnfsidmap.pc (repo-wide convention).
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["nfsidmap"]
        # The plugins live in lib/libnfsidmap and are loaded by name
        # ("<method>.so") through the loader search path, so advertise that
        # directory too: consumers then get it on LD_LIBRARY_PATH from the
        # Conan run environment.
        self.cpp_info.libdirs = ["lib", "lib/libnfsidmap"]
        self.cpp_info.set_property("pkg_config_name", "libnfsidmap")
