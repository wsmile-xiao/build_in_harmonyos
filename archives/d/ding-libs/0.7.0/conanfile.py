#!/usr/bin/env python3
"""Conan recipe for ding-libs 0.7.0.

The release tarball contains pregenerated Autotools files.  The recipe keeps
both upstream libraries (dhash and ini_config) and runs the complete upstream
check suite on OHOS.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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


class DingLibsConan(ConanFile):
    name = "ding-libs"
    version = "0.7.0"
    description = "SSSD utility libraries: dynamic hash tables and INI configuration"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/SSSD/ding-libs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ding-libs supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "ding-libs OHOS support is validated for armv8/AArch64"
            )

    def build_requirements(self):
        # Regenerate the release tarball's Autotools files from configure.ac and
        # Makefile.am after applying source-level patches.  This keeps generated
        # configure/Makefile.in files out of the patch set and makes the build
        # reproducible on workers without user-installed Autotools.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

        # Only the upstream Check-based tests need this dependency; it is not
        # part of the installed ding-libs link interface.
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # check.pc is consumed by configure when HAVE_CHECK is detected.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        check = self._dependency("check")
        if check is not None:
            # The upstream dhash target has a historical CFLAGS typo.  Keep
            # Check's include directory in the recipe toolchain so the target
            # compiles without patching generated Makefile.in.
            check_include = os.path.join(check.package_folder, "include")
            if os.path.isdir(check_include):
                tc.extra_cflags.append(f"-I{check_include}")
        tc.configure_args.extend(
            [
                "--disable-nls",
                "--disable-dependency-tracking",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
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
        # PkgConfigDeps writes check.pc into the generators directory.  Keep
        # the profile's existing search path while putting generated metadata
        # first.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        if str(self.settings.os) == "OHOS":
            # /tmp is read-only on the target.  Check 0.15.2 also consults
            # TEMP before P_tmpdir, so set all common spellings explicitly.
            test_tmp = os.path.join(self.build_folder, "tmp")
            os.makedirs(test_tmp, exist_ok=True)
            env.define("TMPDIR", test_tmp)
            env.define("TMP", test_tmp)
            env.define("TEMP", test_tmp)
            if for_tests:
                # Check's forked runner uses temporary IPC files, which are
                # restricted on HMDFS.  In-process mode keeps all 20 tests.
                env.define("CK_FORK", "no")
                check = self._dependency("check")
                if check is not None:
                    check_libdir = os.path.join(check.package_folder, "lib")
                    if os.path.isdir(check_libdir):
                        # This is scoped to make check only; it never leaks
                        # into compiler/linker discovery during the build.
                        env.prepend_path("LD_LIBRARY_PATH", check_libdir)
        return env

    def build(self):
        apply_conandata_patches(self)

        # The source-level configure.ac patch changes Autoconf's temporary
        # directory umask.  Recreate configure and Makefile.in after applying
        # patches rather than committing generated-file diffs (R6).
        automake = self._dependency("automake")
        automake_share = ""
        if automake is not None:
            automake_share = os.path.join(
                automake.package_folder, "share", "automake-1.18"
            )
        # The Conan Perl package is ABI-incompatible with the native OHOS Perl
        # used by the Automake scripts.  Override both variables on each
        # command: Conan's aggregated build env otherwise restores the Perl
        # package's incompatible PERL5LIB after a context manager exits.
        bootstrap_prefix = (
            'PERL="/data/service/hnp/bin/perl" '
            f'PERL5LIB="{automake_share}" '
        )
        self.run(
            f"{bootstrap_prefix}aclocal --force -I m4",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            f"{bootstrap_prefix}autoconf --force",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            f"{bootstrap_prefix}automake --add-missing --copy",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # HMDFS: once Conan has created the build tree the parent directories are
        # no longer reachable through getcwd(), so the `pwd` probe that Autoconf
        # runs before re-executing configure under CONFIG_SHELL=bash fails with
        # "working directory cannot be determined".  Publishing the logical $PWD
        # lets the shell resolve the directory without calling getcwd(), the same
        # workaround the adms / aribb24 / aircrack recipes use.
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._environment().vars(self).apply():
            autotools.configure()
            autotools.make(
                args=[
                    "-j1",
                    "ACLOCAL=true",
                    "AUTOMAKE=true",
                    "AUTOCONF=true",
                    "AUTOHEADER=true",
                ]
            )

        # Run every upstream Automake test, not a reduced smoke subset.
        with VirtualBuildEnv(self).vars().apply(), self._environment(
            for_tests=True
        ).vars(self).apply():
            autotools.make(
                target="check",
                args=[
                    "-j1",
                    "ACLOCAL=true",
                    "AUTOMAKE=true",
                    "AUTOCONF=true",
                    "AUTOHEADER=true",
                ],
            )

    def package(self):
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._environment().vars(self).apply():
            autotools.install(
                args=[
                    "-j1",
                    "ACLOCAL=true",
                    "AUTOMAKE=true",
                    "AUTOCONF=true",
                    "AUTOHEADER=true",
                ]
            )

        # Libtool archives contain the build-time absolute libdir and are not
        # needed by Conan consumers; cpp_info/pkg-config provide link metadata.
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(
            self,
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ding-libs")
        self.cpp_info.set_property("cmake_target_name", "ding-libs::ding-libs")
        self.cpp_info.set_property("pkg_config_name", "ding-libs")

        dhash = self.cpp_info.components["dhash"]
        dhash.libs = ["dhash"]
        dhash.set_property("cmake_target_name", "ding-libs::dhash")
        dhash.set_property("pkg_config_name", "dhash")

        ini = self.cpp_info.components["ini_config"]
        ini.libs = ["ini_config"]
        ini.set_property("cmake_target_name", "ding-libs::ini_config")
        ini.set_property("pkg_config_name", "ini_config")

        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
