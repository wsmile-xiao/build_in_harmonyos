#!/usr/bin/env python3
"""Conan recipe — kea-admin 3.0.3 (ISC Kea database administration tool).

``kea-admin`` is the administration tool ISC Kea ships for its lease
databases; its sources live in ``src/bin/admin`` of the Kea 3.0.3 release
tarball.  The tool is a **POSIX shell script**: the upstream Meson target
(``src/bin/admin/meson.build``) declares no compilation and no
``dependencies:``/``link_with:`` at all.  Its sole build actions are
``configure_file()`` -- expanding ``kea-admin.in`` into the ``kea-admin``
script and ``admin-utils.sh.in`` into the shared helper, and materialising the
database maintenance scripts (40 mysql and 34 pgsql ``upgrade_*.sh``, plus the
schema creation/drop scripts and ``wipe_data.sh``) under
``src/share/database/scripts``.

The recipe therefore stops after the upstream configure phase, which is the
step that produces every artefact, and packages the generated script together
with the shared scripts tree (``share/kea/scripts``).  There is nothing to
compile and nothing to link for this package.

Kea builds as a single Meson project, so ``meson setup`` still evaluates the
project-level dependency gate in the top-level ``meson.build`` (boost is
required without a fallback, openssl is the mandatory default crypto back-end,
log4cplus comes from a wrap fallback).  Those dependencies are declared here
because the upstream configure step cannot run without them; they are consumed
by the configure probes only and are not linked into the shipped artefacts, so
``package_info()`` does not propagate them to consumers.

Platform adaptation lives in ``patches/``: the Meson system-name normalization
(OpenHarmony is reported as ``harmonyos``, which Kea's platform branch does not
recognize), the relocation of the script's runtime pieces (upstream bakes the
configure-time absolute prefix, and the resulting ``/share/kea`` path does not
exist inside a Conan package), and the interpreter prefixes required by the
HarmonyOS PC kernel, which refuses ``execve()`` of ``#!/bin/sh`` scripts
regardless of the executable bits: kea-admin and the database maintenance
scripts are started through ``sh``, and the Meson steps are replicated here so
the ``meson`` wrapper (itself a shell script) can be invoked the same way.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class KeaAdminConan(ConanFile):
    name = "kea-admin"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 database administration tool (kea-admin) for "
                   "the mysql/pgsql lease databases")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Upstream Meson test entry covering this package: the admin error-reporting
    # suite (src/bin/admin/tests/meson.build, suite 'shell-tests'), which drives
    # kea-admin through its argument-validation paths without needing a
    # database back-end.  The memfile suite needs the kea-dhcp4/kea-dhcp6/
    # kea-lfc binaries (separate targets of the same Meson project, not part of
    # this package) and the mysql/pgsql suites are registered only when those
    # back-ends are configured (this recipe configures them off).
    upstream_test_targets = ("admin_tests.sh",)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Project-level configure gate of the Kea Meson build.  boost must be
        # pinned: the 1.90/1.91 packages miss boost/interprocess,
        # boost/circular_buffer and other headers that Kea probes for with
        # required: true.
        self.requires("boost/1.85.0")
        self.requires("log4cplus/2.2.0.1")
        self.requires("openssl/3.5.8.1")

    def build_requirements(self):
        # Kea needs meson >= 1.10: the boost packages ship no libboost_system,
        # which only resolves through the header-only module fallback added in
        # meson 1.10.
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
        # them explicitly so the configure does not depend on host-side probes.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "disabled"
        tc.project_options["netconf"] = "disabled"
        tc.project_options["krb5"] = "disabled"
        # The OHOS musl <pthread.h> does not declare pthread_setcancelstate(),
        # which boost/core/detail/sp_thread_sleep.hpp calls (used through
        # Boost.Asio).  The upstream escape hatch keeps the boost probes
        # compiling.
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

    def _meson(self):
        # bin/meson in the Conan meson package is a shebang shell wrapper;
        # invoke it through sh so it runs on HarmonyOS PC too (see the module
        # docstring).  Returns the ready-made command prefix.
        meson_bin = os.path.join(self.dependencies.build["meson"].package_folder,
                                 "bin", "meson")
        return 'sh "{}"'.format(meson_bin)

    def build(self):
        apply_conandata_patches(self)
        # Replicate conan's Meson helper command line (same --native-file,
        # build dir, source dir and --prefix), only with the sh-prefixed
        # wrapper.  The admin targets have no compilation step: configure_file()
        # already writes kea-admin, admin-utils.sh and the database scripts into
        # the build tree during this call.
        native_file = os.path.join(self.build_folder, "conan",
                                   "conan_meson_native.ini")
        meson = self._meson()
        self.run('{} setup --native-file "{}" "{}" "{}" --prefix=/'.format(
            meson, native_file, self.build_folder, self.source_folder))
        if self.options.tests:
            # Error-reporting suite of kea-admin; needs no database back-end and
            # no compiled target (the registration runs the script through sh,
            # see patches 0004/0005).  --timeout-multiplier 4: the suite spawns
            # one kea-admin process per argument-validation case and exceeds
            # meson's default 30 s per-test budget on the OHOS device and on
            # loaded CI workers.
            self.run('{} test -v --timeout-multiplier 4 -C "{}" {}'.format(
                meson, self.build_folder, " ".join(self.upstream_test_targets)))

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # The generated script resolves admin-utils.sh and the maintenance
        # scripts relative to its own location (<root>/bin -> <root>/share),
        # mirroring the upstream install layout (SBINDIR + DATADIR/kea/scripts).
        scripts_dir = os.path.join(self.package_folder, "share", "kea", "scripts")
        copy(self, "kea-admin",
             src=os.path.join(self.build_folder, "src", "bin", "admin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "admin-utils.sh",
             src=os.path.join(self.build_folder, "src", "bin", "admin"),
             dst=scripts_dir)
        copy(self, "*",
             src=os.path.join(self.build_folder, "src", "share", "database", "scripts", "mysql"),
             dst=os.path.join(scripts_dir, "mysql"))
        copy(self, "*",
             src=os.path.join(self.build_folder, "src", "share", "database", "scripts", "pgsql"),
             dst=os.path.join(scripts_dir, "pgsql"))
        os.chmod(os.path.join(self.package_folder, "bin", "kea-admin"), 0o755)

    def package_info(self):
        # Command-line tool: nothing to link or include, only PATH for the
        # script.  The tool is started through sh ("sh <package>/bin/kea-admin"):
        # the HarmonyOS PC kernel refuses execve() of shebang scripts.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
