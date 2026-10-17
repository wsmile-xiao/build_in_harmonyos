#!/usr/bin/env python3
"""Conan recipe — kea-hook-pgsql 3.0.3 (ISC Kea PostgreSQL back-end hook, Meson).

The target is the PostgreSQL back-end hook plug-in of ISC Kea 3.0.3, built from
``src/hooks/dhcp/pgsql`` as ``libdhcp_pgsql.so``.  It provides the PostgreSQL
configuration back-end, host data source, forensic (legal) log and lease
manager to kea-dhcp4/kea-dhcp6 and is loaded by the server at run time with
dlopen() (``hooks-libraries``).  Kea 3.0 replaced Autotools with Meson and
builds the whole tree in one project, so the recipe builds the upstream tree
and packages the plug-in together with the Kea shared libraries it loads at
run time (see ``kea_runtime_libs``) and the PostgreSQL schema scripts it
operates on (``share/kea/scripts/pgsql``).

Platform adaptations live in ``patches/`` (Meson system detection and the
musl/UAPI ``sockaddr_storage`` collision); the remaining platform gaps are
handled from the toolchain in :meth:`generate`.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class KeaHookPgsqlConan(ConanFile):
    name = "kea-hook-pgsql"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 PostgreSQL back-end hook plug-in (libdhcp_pgsql.so) "
                   "for kea-dhcp4/kea-dhcp6, with the Kea runtime libraries it loads "
                   "and the pgsql schema scripts")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Kea shared libraries loaded by the plug-in (the NEEDED closure of
    # libdhcp_pgsql.so, resolved with readelf on the built artefact; includes
    # libkea-pgsql, the PostgreSQL exchange/connection helper library built by
    # src/lib/pgsql once -Dpostgresql=enabled).
    kea_runtime_libs = (
        "libkea-asiolink", "libkea-cc", "libkea-cfgrpt", "libkea-config",
        "libkea-cryptolink", "libkea-database", "libkea-dhcp", "libkea-dhcp_ddns",
        "libkea-dhcpsrv", "libkea-dns", "libkea-eval", "libkea-exceptions",
        "libkea-hooks", "libkea-http", "libkea-log", "libkea-log-interprocess",
        "libkea-pgsql", "libkea-process", "libkea-stats", "libkea-tcp",
        "libkea-util",
    )
    # Upstream Meson suite covering the plug-in contract that is runnable
    # without a live PostgreSQL server.  The remaining suites registered by
    # this plug-in (dhcp-pgsql-lib-tests, kea-pgsql-tests) require a live
    # PostgreSQL instance preloaded with the keatest schema; they are built
    # but not executed here and are declared in test_package/MANIFEST.yml.
    upstream_test_suites = ("dhcp-pgsql-libload-tests",)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the Kea 3.0.3 build.  boost is
        # pinned: 1.90/1.91 packages miss boost/interprocess, circular_buffer,
        # format and assign headers that Kea actually includes.
        self.requires("boost/1.85.0")
        self.requires("log4cplus/2.2.0.1")
        self.requires("openssl/3.5.8.1")
        # PostgreSQL frontend client library: the hook and libkea-pgsql link
        # against it (top-level meson.build probes dependency('libpq') via
        # pkg-config when -Dpostgresql=enabled).
        self.requires("libpq/18.6")

    def build_requirements(self):
        # Kea requires meson >= 1.10 here: the boost packages ship no
        # libboost_system, which only resolves through the header-only module
        # fallback added in meson 1.10.
        self.tool_requires("meson/1.11.0")
        if self.options.tests:
            self.test_requires("gtest/1.17.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "enabled" if self.options.tests else "disabled"
        # Optional back-ends: postgresql is the target of this package and is
        # resolved through the libpq Conan dependency; mysql/netconf/krb5 have
        # no Conan dependency here and are disabled explicitly so the build
        # does not depend on host-side probes.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "enabled"
        tc.project_options["netconf"] = "disabled"
        tc.project_options["krb5"] = "disabled"
        # The OHOS musl <pthread.h> does not declare pthread_setcancelstate(),
        # which boost/core/detail/sp_thread_sleep.hpp calls (used through
        # Boost.Asio).  The upstream escape hatch keeps it compiling.
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        # Meson probes the static linker in project(); the CI workers do not
        # expose llvm-ar/llvm-ranlib on PATH, so derive them from the configured
        # compiler location.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()
        # Meson runs compile-and-run feature probes during configure (log4cplus,
        # openssl, boost), so the shared dependencies must be resolvable at run
        # time while configuring.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("conanbuildenv-kea-runtime")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if self.options.tests:
            # Run the plug-in load/unload contract suite; it dlopen()s the
            # built libdhcp_pgsql.so through the Kea hook framework and needs
            # no database.  The DB-backed suites are not runnable without a
            # live PostgreSQL server + keatest schema (see MANIFEST.yml).
            self.run('meson test -v -C "{}" {}'.format(
                self.build_folder, " ".join(self.upstream_test_suites)))

    def _is_kea_runtime_lib(self, name):
        if name.endswith(".symbols"):  # meson SHSYM intermediate, not shipped
            return False
        return any(name == "{}.so".format(lib) or name.startswith("{}.so.".format(lib))
                   for lib in self.kea_runtime_libs)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libdhcp_pgsql.so",
             src=os.path.join(self.build_folder, "src", "hooks", "dhcp", "pgsql"),
             dst=os.path.join(self.package_folder, "lib", "kea", "hooks"))
        # Kea runtime libraries.  Recreate the upstream soname symlinks instead
        # of letting the copy follow them, which would store every library three
        # times over.
        lib_dst = os.path.join(self.package_folder, "lib")
        for root, _dirs, files in os.walk(os.path.join(self.build_folder, "src", "lib")):
            for name in files:
                if not self._is_kea_runtime_lib(name):
                    continue
                src_path = os.path.join(root, name)
                dst_path = os.path.join(lib_dst, name)
                if os.path.islink(src_path):
                    if os.path.exists(dst_path) or os.path.islink(dst_path):
                        os.remove(dst_path)
                    try:
                        os.symlink(os.readlink(src_path), dst_path)
                        continue
                    except OSError:
                        # Filesystems without symlink support: fall back to a copy.
                        pass
                copy(self, name, src=root, dst=lib_dst)
        # PostgreSQL schema scripts used to initialise/drop the Kea database
        # (upstream installs them to share/kea/scripts/pgsql).  The two SQL
        # scripts are plain data files; the shell wrappers (wipe_data.sh,
        # upgrade_*.sh) are configure_file() outputs that embed the build-time
        # prefix, so they are intentionally not packaged — they remain
        # available from the upstream source tree.
        copy(self, "*.pgsql",
             src=os.path.join(self.source_folder, "src", "share", "database", "scripts", "pgsql"),
             dst=os.path.join(self.package_folder, "share", "kea", "scripts", "pgsql"))

    def package_info(self):
        # The package ships a Kea hook plug-in, which is dlopen()-ed by the Kea
        # server at runtime and is not linked against, so there is no public
        # library to link or header to include.  libdirs is kept so that
        # consumers' runtime environment points at the packaged Kea libraries;
        # libpq.so.5 itself resolves through the libpq dependency of this
        # package.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
