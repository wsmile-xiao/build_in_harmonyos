#!/usr/bin/env python3
"""Conan recipe — das-watchdog 0.9.0

Realtime-process watchdog CLI for Linux (kmatheussen/das_watchdog).
Build system: plain Makefile (no configure). The Makefile discovers
libgtop through `pkg-config libgtop-2.0`, so PkgConfigDeps supplies the
generated .pc for the libgtop/2.41.3 dependency.
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
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class DasWatchdogConan(ConanFile):
    name = "das-watchdog"
    version = "0.9.0"
    description = "A general watchdog for the linux operating system that should run in the background at all times to ensure a realtime process won't hang the machine"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kmatheussen/das_watchdog"
    url = "https://github.com/kmatheussen/das_watchdog"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libgtop/2.41.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"das-watchdog supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Makefile FLAGS runs `pkg-config --libs --cflags libgtop-2.0`; the
        # generated libgtop-2.0.pc (and transitive glib .pc) land in the
        # generators folder. Export PKG_CONFIG_PATH through a dedicated
        # build-scope script so VirtualBuildEnv aggregates it into conanbuild.
        PkgConfigDeps(self).generate()
        environment = Environment()
        environment.append_path("PKG_CONFIG_PATH", self.generators_folder)
        environment.vars(self, scope="build").save_script("daswatchdog_pkgconfig")
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder, env="conanbuild")

    def package(self):
        # CLI tool: install the das_watchdog binary to bin/
        copy(self, "das_watchdog", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
