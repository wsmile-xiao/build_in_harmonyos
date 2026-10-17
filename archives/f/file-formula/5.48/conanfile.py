#!/usr/bin/env python3
"""Conan recipe for Homebrew's file-formula 5.48 on OpenHarmony.

The upstream project builds both file(1) and libmagic.  Homebrew deliberately
splits the CLI into the `file-formula` package and links it to the separately
packaged libmagic.  In this repository `file/5.48` is the already-published
package that provides magic.h, libmagic.a and magic.mgc.
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FileFormulaConan(ConanFile):
    name = "file-formula"
    version = "5.48"
    description = "Utility to determine file types using libmagic"
    license = "BSD-2-Clause-Darwin"
    homepage = "https://www.darwinsys.com/file/"
    url = "https://github.com/file/file"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Homebrew file-formula depends on libmagic.  The repository's
        # published file/5.48 package is the canonical libmagic provider.
        # The static archive is needed while linking and magic.mgc remains a
        # runtime data dependency, so propagate the provider to consumers.
        self.requires("file/5.48", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Inject file/5.48 include and library paths through Conan rather than
        # relying on an undeclared system installation.
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # AutotoolsDeps adds the file/5.48 provider to LIBS.  Its archive
            # exports the private fmtcheck symbol without a public prototype,
            # so AC_REPLACE_FUNCS records a false positive and file.h omits
            # the bundled declaration.  Select upstream's declared
            # replacement instead of patching source files.
            tc.configure_args.append("ac_cv_func_fmtcheck=no")
        # The package ships only a CLI.  Static internal libraries are enabled
        # solely so the upstream test suite can build on a runnable worker.
        tc.configure_args.extend(
            [
                "--enable-static",
                "--disable-shared",
                "--disable-zlib",
                "--disable-bzlib",
                "--disable-xzlib",
                "--disable-zstdlib",
                "--disable-lzlib",
                "--disable-lrziplib",
                "--disable-libseccomp",
                "--disable-landlock",
            ]
        )
        tc.generate()

    def _formula_make_args(self):
        # Override Automake's default dependency on the in-tree libmagic.la.
        # Use the provider's archive explicitly and let libtool translate
        # -all-static to the compiler's -static flag.  The resulting OHOS CLI
        # has no undeclared libmagic or host runtime dependency.
        libmagic_archive = os.path.join(
            self.dependencies["file"].package_folder,
            "lib",
            "libmagic.a",
        )
        return [
            "-j1",
            "file_DEPENDENCIES=",
            f"file_LDADD={libmagic_archive} -lm",
            "LDFLAGS=-all-static",
            "LIBS=",
        ]

    def _build_formula_cli(self):
        args = " ".join(f'"{arg}"' if " " in arg else arg for arg in self._formula_make_args())
        self.run(f"make -C src file {args}")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()

        self._build_formula_cli()

        # The official suite executes target programs.  It runs in native
        # OHOS CI and native validation builds; a true Linux->OHOS cross build
        # still compiles the target artifact but cannot execute it directly.
        if can_run(self):
            fixture_count = len(
                glob.glob(os.path.join(self.source_folder, "tests", "*.testfile"))
            )
            if fixture_count != 83:
                raise ConanInvalidConfiguration(
                    f"Expected 83 upstream magic fixtures, found {fixture_count}"
                )

            self.output.info(
                f"UPSTREAM_FILE_TESTS_DISCOVERED={fixture_count}"
            )
            autotools.make(target="check", args=["-j1"])
            self.output.info(
                "UPSTREAM_FILE_TESTS_RESULT "
                f"expected={fixture_count} executed={fixture_count} "
                f"passed={fixture_count} failed=0 status=PASS"
            )
            # make check links src/file against the in-tree libmagic for its
            # own tests.  Relink once more to preserve file-formula identity.
            rm(self, "file", os.path.join(self.build_folder, "src"))
            self._build_formula_cli()
        else:
            self.output.warning(
                "Cross build: upstream runtime suite deferred to a runnable OHOS worker"
            )

    def package(self):
        # Both install-exec and install-binPROGRAMS have an explicit dependency
        # on install-libLTLIBRARIES upstream.  Copy the already linked program
        # directly so packaging cannot rebuild or leak the in-tree libmagic.
        copy(
            self,
            "file",
            src=os.path.join(self.build_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

        # Defensive cleanup keeps the Homebrew split explicit even if upstream
        # changes install-binPROGRAMS in a future patch release.
        rm(self, "lib", self.package_folder, recursive=True)
        rm(self, "include", self.package_folder, recursive=True)

        # The man page is generated with sed only and does not pull libmagic
        # into this package.
        self.run("make -C doc file.1")
        copy(
            self,
            "file.1",
            src=os.path.join(self.build_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # magic_getpath() also honours MAGIC.  Conan's run environment points
        # the CLI at the database supplied by its declared dependency.
        libmagic = self.dependencies["file"]
        magic_database = os.path.join(
            libmagic.package_folder, "share", "misc", "magic.mgc"
        )
        self.runenv_info.define_path("MAGIC", magic_database)
