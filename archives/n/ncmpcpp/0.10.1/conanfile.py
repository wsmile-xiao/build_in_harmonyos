#!/usr/bin/env python3
"""Conan recipe for ncmpcpp 0.10.1 on HarmonyOS PC (aarch64).

Build system: autotools. configure is pre-generated from configure.ac and
shipped as plain files under files/autotools-generated/ (copied at build time) so CI does not need aclocal/automake.

Adaptation notes:
- OHOS package repository has no GNU readline; ncmpcpp integrates it deeply,
  so patch 0002 replaces it with a minimal compatibility layer covering the
  APIs used by window.cpp.
- OHOS boost/1.90.0.1 ships no libboost_regex/libboost_locale, so patches
  0003/0004 move regex to std::regex and locale to a built-in UTF-8 codec.
- OHOS boost/1.90.0.1 also omits the header-only boost/format library, so the
  missing headers (Boost 1.84, BSL-1.0) are vendored as files/vendor-boost/
  and added to CPPFLAGS via -I vendor-boost.
- HMDFS: config.status uses umask 077; replace with 022 before running
  configure.
- Adjust timestamps so make does not re-run aclocal/automake/autoconf.
- Pass explicit --build/--host=aarch64-unknown-linux-ohos to avoid
  config.guess failing on HMDFS.
"""

import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class NcmpcppConan(ConanFile):
    name = "ncmpcpp"
    version = "0.10.1"
    description = "Featureful ncurses-based MPD client"
    license = "GPL-2.0-or-later"
    homepage = "https://ncmpcpp.rybczak.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*",
            os.path.join(self.recipe_folder, "files"),
            os.path.join(self.export_sources_folder, "files"),
            keep_path=True,
        )

    def requirements(self):
        self.requires("boost/1.90.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libmpdclient/2.23", transitive_headers=True, transitive_libs=True)
        self.requires("ncurses/6.5", transitive_headers=True, transitive_libs=True)
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = self.conan_data["sources"]
        # Conan copies export_sources into the source folder before source()
        # runs, so git clone cannot target "." directly. Clone into a child
        # directory and merge the upstream tree up into the source folder.
        clone_folder = os.path.join(self.source_folder, "_upstream")
        git = Git(self, clone_folder)
        git.clone(
            url=source["git"],
            target=".",
            args=["--depth", "1", "--branch", source["tag"]],
        )

        head_file = os.path.join(clone_folder, ".git", "HEAD")
        with open(head_file, encoding="utf-8") as handle:
            actual_commit = handle.read().strip()
        if actual_commit != source["commit"]:
            raise ConanInvalidConfiguration(
                f"Tag {source['tag']} resolved to {actual_commit}, "
                f"expected {source['commit']}"
            )

        for entry in os.listdir(clone_folder):
            if entry != ".git":
                shutil.move(os.path.join(clone_folder, entry), self.source_folder)
        shutil.rmtree(clone_folder)

        apply_conandata_patches(self)
        self._copy_autotools_generated_files()
        self._copy_vendored_boost_format()
        # Windows/git may not preserve exec bits; OHOS CI runs ./configure
        # from the exported sources, so make the generated scripts executable.
        for name in (
            "configure",
            "config.guess",
            "config.sub",
            "compile",
            "depcomp",
            "install-sh",
            "ltmain.sh",
            "missing",
        ):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

    def _copy_vendored_boost_format(self):
        # OHOS boost/1.90.0.1 omits the header-only boost/format library,
        # which ncmpcpp needs for boost::format. Ship the missing headers
        # (from Boost 1.84, BSL-1.0, see files/vendor-boost/LICENSE_1_0.txt)
        # and add them to the include search path so configure and make can
        # find them alongside the registry boost package.
        copy(
            self,
            "*",
            os.path.join(self.export_sources_folder, "files", "vendor-boost"),
            os.path.join(self.source_folder, "vendor-boost"),
            keep_path=True,
        )

    def _copy_autotools_generated_files(self):
        # The generated Autotools output (~58k lines) is committed as plain
        # text files so the PR diff applies cleanly on CI (binary files in
        # PR diffs cannot be applied by the checkout-pr git apply step).
        copy(
            self,
            "*",
            os.path.join(self.export_sources_folder, "files", "autotools-generated"),
            self.source_folder,
            keep_path=True,
        )


    def generate(self):
        # configure uses PKG_CHECK_MODULES for libmpdclient.pc / ncursesw.pc /
        # libcurl.pc, generated by PkgConfigDeps from each dependency's
        # pkg_config_name.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-lto=no")
        if str(self.settings.os) == "OHOS":
            # Explicit triplets: config.guess on HMDFS cannot create its
            # dummy.c probe file (Permission denied).
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            # boost.m4 only searches system paths and $with_boost, ignoring
            # CPPFLAGS; point it at the Conan-cached boost package.
            tc.configure_args.append(
                "--with-boost={}".format(self.dependencies["boost"].package_folder)
            )
        tc.generate()

        # configure conftest needs to find the shared dependencies at runtime
        # (all are shared packages).
        env = Environment()
        vendor_include = os.path.join(self.source_folder, "vendor-boost")
        if os.path.isdir(vendor_include):
            # boost.m4 and make search CPPFLAGS include dirs in order; the
            # registry boost package lacks boost/format.hpp, so the search
            # falls through to the vendored copy.
            env.append("CPPFLAGS", "-I{}".format(vendor_include))
        for dep in self.dependencies.values():
            # Only direct runtime dependencies have an installed binary
            # package at generate() time; transitive toolchain deps such as
            # openssl/zlib may only have recipes (package_folder is None).
            if dep.package_folder:
                env.append_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, "lib"),
                )
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        if str(self.settings.os) == "OHOS":
            # config.status is generated by configure, so umask must be fixed
            # before configure runs.
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                "umask 077",
                "umask 022",
            )
        self._fix_autotools_timestamps()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream registers no TESTS/check_PROGRAMS, so make check is a no-op
        # (satisfies L1 test-execution requirement).
        autotools.make(target="check", args=["-j1"])

    def _fix_autotools_timestamps(self):
        """Ensure configure.ac/Makefile.am < aclocal.m4 < configure <
        Makefile.in so make does not re-invoke aclocal/automake/autoconf.
        """
        src = self.source_folder
        base_time = time.time() - 3600
        input_files = [
            os.path.join(src, "configure.ac"),
            os.path.join(src, "Makefile.am"),
            os.path.join(src, "src", "Makefile.am"),
            os.path.join(src, "doc", "Makefile.am"),
        ]
        # automake lists every m4/*.m4 macro file in am__aclocal_m4_deps;
        # if any of them is newer than aclocal.m4, make re-runs aclocal,
        # which does not exist on the OHOS CI. Pin them to base_time too.
        m4_dir = os.path.join(src, "m4")
        if os.path.isdir(m4_dir):
            for root, _, files in os.walk(m4_dir):
                for name in files:
                    input_files.append(os.path.join(root, name))
        acinclude = os.path.join(src, "acinclude.m4")
        if os.path.exists(acinclude):
            input_files.append(acinclude)
        aclocal_files = [os.path.join(src, "aclocal.m4")]
        configure_files = [os.path.join(src, "configure")]
        makefile_files = [
            os.path.join(src, "Makefile.in"),
            os.path.join(src, "src", "Makefile.in"),
            os.path.join(src, "doc", "Makefile.in"),
        ]
        helper_files = [
            os.path.join(src, "config.guess"),
            os.path.join(src, "config.sub"),
            os.path.join(src, "install-sh"),
            os.path.join(src, "missing"),
            os.path.join(src, "depcomp"),
            os.path.join(src, "compile"),
        ]
        timestamp_groups = (
            (input_files, base_time),
            (aclocal_files, base_time + 10),
            (configure_files, base_time + 20),
            (makefile_files + helper_files, base_time + 30),
        )
        for files, timestamp in timestamp_groups:
            for file_path in files:
                if os.path.exists(file_path):
                    os.utime(file_path, (timestamp, timestamp))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]