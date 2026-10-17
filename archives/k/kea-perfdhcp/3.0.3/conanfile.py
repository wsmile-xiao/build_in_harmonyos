#!/usr/bin/env python3
"""Conan recipe — kea-perfdhcp 3.0.3 (ISC Kea DHCP benchmarking tool, Meson).

``perfdhcp`` is the DHCPv4/DHCPv6 performance-testing client that ISC Kea
ships; its sources live in ``src/bin/perfdhcp`` of the Kea 3.0.3 release
tarball and the Meson target installs the executable into ``SBINDIR``.  Kea 3.0
replaced Autotools with Meson and builds the whole tree as a single project, so
the recipe builds the upstream tree and packages the client together with the
Kea shared libraries it loads at runtime (see ``kea_runtime_libs``).

Platform adaptations live in ``patches/`` (the Meson system-name normalization
and the musl/UAPI ``sockaddr_storage`` collision); the remaining platform gaps
are handled from the toolchain in :meth:`generate`.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class KeaPerfdhcpConan(ConanFile):
    name = "kea-perfdhcp"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 DHCPv4/DHCPv6 performance-testing client (perfdhcp), "
                   "with the Kea runtime libraries it loads")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Upstream Meson test target covering this package (src/bin/perfdhcp/tests,
    # suite 'perfdhcp-tests'), run from build() below.
    upstream_test_suites = ("perfdhcp-tests",)
    # Kea shared libraries loaded by the client (the NEEDED closure of the
    # perfdhcp binary, resolved with readelf on the built artefact).
    kea_runtime_libs = (
        "libkea-asiolink", "libkea-cc", "libkea-cryptolink", "libkea-dhcp",
        "libkea-dns", "libkea-exceptions", "libkea-hooks", "libkea-log",
        "libkea-log-interprocess", "libkea-util",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the Kea 3.0.3 build.  boost is
        # pinned: 1.90/1.91 packages miss boost/interprocess, circular_buffer,
        # format and assign headers that Kea actually includes.
        self.requires("boost/1.85.0")
        self.requires("log4cplus/2.2.0.1")
        self.requires("openssl/3.5.8.1")

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
        # Optional back-ends: no Conan dependency is provided for them, disable
        # them explicitly so the build does not depend on host-side probes.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "disabled"
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
        # Fully qualified target names: src/bin/perfdhcp/meson.build declares a
        # static library and an executable, both named 'perfdhcp', so the bare
        # name is ambiguous for 'meson compile'.
        meson.build(target="./src/bin/perfdhcp/perfdhcp:executable")
        if self.options.tests:
            meson.build(target="./src/bin/perfdhcp/tests/perfdhcp-tests:executable")
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
        # Upstream installs the client into SBINDIR; Conan packages keep
        # executables under bin/, which is what L0k/L2 and consumers expect.
        copy(self, "perfdhcp",
             src=os.path.join(self.build_folder, "src", "bin", "perfdhcp"),
             dst=os.path.join(self.package_folder, "bin"))
        # Kea runtime libraries.  Recreate the upstream soname symlinks instead
        # of letting the copy follow them, which would store every library
        # several times over.
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

    def package_info(self):
        # Command-line tool: the executable goes on PATH and the Kea libraries
        # it loads at run time stay in lib/ so the generated run environment
        # resolves them (the binary's upstream install RPATH points at the
        # build-machine prefix, which a Conan package cannot rely on).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
