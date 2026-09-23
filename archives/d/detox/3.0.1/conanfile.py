#!/usr/bin/env python3
"""Conan recipe for detox 3.0.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DetoxConan(ConanFile):
    name = "detox"
    version = "3.0.1"
    description = "Command-line utility that cleans unsafe file names"
    license = "BSD-3-Clause"
    homepage = "https://github.com/dharple/detox"
    url = "https://github.com/dharple/detox"
    package_type = "application"
    win_bash = True

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"detox supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--with-check",
                "--disable-dependency-tracking",
            ]
        )
        toolchain.generate()

    def _build_environment(self, for_tests=False):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.define("PKG_CONFIG", "pkgconf")
        if str(self.settings_build.os) == "Windows":
            env.define("MSYS2_ARG_CONV_EXCL", "*")

        temporary = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary, exist_ok=True)
        env.define("TMPDIR", temporary)
        env.define("TMP", temporary)
        env.define("TEMP", temporary)

        if for_tests:
            try:
                check = self.dependencies.test["check"]
            except KeyError:
                check = None
            if check is not None:
                check_libdir = os.path.join(check.package_folder, "lib")
                if os.path.isdir(check_libdir):
                    env.prepend_path("LD_LIBRARY_PATH", check_libdir)

        return env

    @staticmethod
    def _patch_configure_umask(configure_path):
        """Keep Autoconf temporary directories writable on HMDFS."""
        configure_path = os.fspath(configure_path)
        with open(configure_path, "r", encoding="utf-8", newline="") as handle:
            content = handle.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)

    def _stage_test_fixtures(self):
        """Mirror source-only fixtures needed by out-of-source tests."""
        copy(
            self,
            "test_table_resize.tbl",
            src=os.path.join(self.source_folder, "tests", "unit", "fixtures"),
            dst=os.path.join(self.build_folder, "tests", "unit", "fixtures"),
            keep_path=False,
        )

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask(os.path.join(self.source_folder, "configure"))
        generated_files = ["aclocal.m4", "configure", "src/config.h.in"]
        for root, _, files in os.walk(self.source_folder):
            if "Makefile.in" in files:
                generated_files.append(
                    os.path.relpath(
                        os.path.join(root, "Makefile.in"), self.source_folder
                    )
                )

        for generated_file in generated_files:
            generated_path = os.path.join(self.source_folder, generated_file)
            if os.path.isfile(generated_path):
                os.utime(generated_path, None)

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._build_environment().vars(
            self
        ).apply():
            source_folder = os.path.relpath(
                self.source_folder, self.build_folder
            ).replace(os.sep, "/")
            autotools.configure(args=[f"--srcdir={source_folder}"])
            autotools.make(args=["-j1"])

        self._stage_test_fixtures()
        if not can_run(self):
            with VirtualBuildEnv(self).vars().apply(), self._build_environment().vars(
                self
            ).apply():
                autotools.make(
                    target="check-am",
                    args=["-C", "tests/unit", "TESTS=", "-j1"],
                )
            self.output.warning(
                "Built upstream test programs but skipped execution while cross-building"
            )
            return

        with VirtualBuildEnv(self).vars().apply(), self._build_environment(
            for_tests=True
        ).vars(self).apply():
            autotools.make(target="check", args=["-j1", "VERBOSE=yes"])

    def package(self):
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), self._build_environment().vars(
            self
        ).apply():
            autotools.install(args=["-j1"])

        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
