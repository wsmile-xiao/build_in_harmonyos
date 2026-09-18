#!/usr/bin/env python3
"""Conan recipe — kea-hooks 3.0.3 (ISC Kea hooks framework library, Meson).

``kea-hooks`` is the Kea callout framework itself: the ``libkea-hooks`` shared
library built from ``src/lib/hooks`` of ISC Kea 3.0.3.  It implements the hook
machinery (``ServerHooks``, ``CalloutHandle``/``CalloutManager``,
``LibraryManager``, ``HookLibInfo``) that kea-dhcp4/kea-dhcp6 and every user
hook library are built against, and it links against the rest of the Kea
libraries, which the package therefore ships as well.

Kea 3.0 builds the whole tree as a single Meson project, so the recipe drives
Meson directly and compiles just the targets this package owns — the hooks
library (plus the Kea libraries it links against) and the upstream test
executable — rather than the ~1250 unrelated targets of the Kea servers.

Platform adaptations live in ``patches/`` (the Meson platform-name detection);
the three remaining platform gaps are handled from the toolchain in
:meth:`generate`.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class KeaHooksConan(ConanFile):
    name = "kea-hooks"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 hooks (callout) framework library (libkea-hooks.so), "
                   "with the Kea runtime libraries it links against")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # The library this package is about.
    kea_hooks_lib = "libkea-hooks"
    # Kea shared libraries the hooks library links against (its DT_NEEDED
    # closure, resolved with readelf on the built artefact), mapped to the
    # source sub-directory that carries their public headers.  There is no
    # separate Kea package yet, so the closure travels with this one to keep
    # the library loadable.
    kea_runtime_libs = (
        ("libkea-asiolink", "asiolink"),
        ("libkea-cc", "cc"),
        ("libkea-cryptolink", "cryptolink"),
        ("libkea-exceptions", "exceptions"),
        ("libkea-log", "log"),
        ("libkea-log-interprocess", "log/interprocess"),
        ("libkea-util", "util"),
    )
    # Upstream Meson test suite covering the hooks framework: the gtest
    # executable registered in src/lib/hooks/tests/meson.build and the ten
    # fixture libraries it loads at runtime (the ``depends:`` list of the
    # upstream test() definition).
    upstream_test_suites = ("kea-hooks-tests",)
    upstream_test_fixtures = ("nvl", "ivl", "fxl", "bcl", "lcl", "lecl", "ucl",
                              "fcl", "pcl", "acl")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory third-party dependencies of the Kea 3.0.3 build.  boost is
        # pinned: 1.90/1.91 packages miss boost/interprocess, circular_buffer,
        # format and assign headers that Kea actually includes.  All three are
        # needed to compile the packaged headers (they appear in the include
        # chain of kea/hooks, kea/cc, kea/asiolink, kea/log), hence
        # transitive_headers.
        self.requires("boost/1.85.0", transitive_headers=True)
        self.requires("log4cplus/2.2.0.1", transitive_headers=True)
        self.requires("openssl/3.5.8.1", transitive_headers=True)

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
        # Meson probes the static linker in project(); the OHOS build machines
        # do not expose llvm-ar/llvm-ranlib on PATH, so derive them from the
        # configured compiler location.
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
        targets = [self.name]
        if self.options.tests:
            targets += list(self.upstream_test_suites) + list(self.upstream_test_fixtures)
        self.run('meson compile -C "{}" {}'.format(self.build_folder, " ".join(targets)))
        if self.options.tests:
            # --no-rebuild: the targets above are already built; without it meson
            # would rebuild the whole Kea project before running the suite.
            self.run('meson test -v --no-rebuild -C "{}" {}'.format(
                self.build_folder, " ".join(self.upstream_test_suites)))

    def _is_packaged_lib(self, name):
        if name.endswith(".symbols"):  # meson SHSYM intermediate, not shipped
            return False
        libs = (self.kea_hooks_lib, ) + tuple(lib for lib, _ in self.kea_runtime_libs)
        return any(name == "{}.so".format(lib) or name.startswith("{}.so.".format(lib))
                   for lib in libs)

    def _copy_kea_libraries(self):
        """Ship the built Kea libraries, recreating the soname symlinks."""
        lib_dst = os.path.join(self.package_folder, "lib")
        for root, dirs, files in os.walk(os.path.join(self.build_folder, "src", "lib")):
            dirs[:] = [d for d in dirs if not d.endswith(".p")]
            for name in files:
                if not self._is_packaged_lib(name):
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

    def _copy_kea_headers(self):
        """Copy the public headers as upstream installs them: include/kea/<lib>."""
        for lib, srcdir in ((self.kea_hooks_lib, "hooks"), ) + tuple(self.kea_runtime_libs):
            src_root = os.path.join(self.source_folder, "src", "lib", srcdir)
            dst_root = os.path.join(self.package_folder, "include", "kea", srcdir)
            for root, dirs, files in os.walk(src_root):
                dirs[:] = [d for d in dirs if d != "tests"]
                for name in files:
                    if not name.endswith(".h"):
                        continue
                    relative = os.path.relpath(os.path.join(root, name), src_root)
                    dst_path = os.path.join(dst_root, relative)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(os.path.join(root, name), dst_path)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._copy_kea_libraries()
        self._copy_kea_headers()

    def package_info(self):
        self.cpp_info.libs = ["kea-hooks"]
        self.cpp_info.bindirs = []
        # Kea installs its headers under <prefix>/include/kea and includes them
        # as <hooks/hooks.h>, <util/...>, so the include root is include/kea.
        self.cpp_info.includedirs = [os.path.join("include", "kea")]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os == "OHOS":
            # The packaged Kea headers reach boost/core/detail/sp_thread_sleep.hpp
            # (through Boost.Asio and boost/shared_ptr.), which calls
            # pthread_setcancelstate() that the OHOS musl pthread.h does not
            # declare.  Consumers need the same boost escape hatch this recipe
            # uses while building.
            self.cpp_info.defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
