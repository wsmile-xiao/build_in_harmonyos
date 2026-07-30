#!/usr/bin/env python3
"""Conan recipe for duc on OpenHarmony."""

from conan import ConanFile
from conan.tools.build import can_run
import os

from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps


class DucConan(ConanFile):
    name = "duc"
    version = "1.4.6"
    description = "Disk usage index, inspection, and visualization tools"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/zevv/duc"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/",
            "--build=aarch64-linux-gnu",
            "--with-db-backend=sqlite3",
            "--disable-cairo",
            "--disable-x11",
            "--disable-ui",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        previous_pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = (
            f"{self.generators_folder}:{previous_pkg_config_path}"
        ).rstrip(":")
        try:
            autotools.configure()
        finally:
            if previous_pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = previous_pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)
        autotools.make(args=["-j1"])
        if can_run(self):
            test_script = os.path.join(self.source_folder, "test.sh")
            if os.path.exists(test_script):
                self.run(test_script, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
