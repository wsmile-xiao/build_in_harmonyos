#!/usr/bin/env python3
"""Conan recipe for libfuse (fuse3) 3.18.2 — OHOS-ready.

Build system: Meson
Upstream: https://github.com/libfuse/libfuse
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
import os


class LibfuseConan(ConanFile):
    name = "libfuse"
    version = "3.18.2"
    description = "libfuse — Filesystem in Userspace (fuse3)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libfuse/libfuse"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os not in ("Linux", "FreeBSD", "OHOS"):
            raise ConanInvalidConfiguration("libfuse supports only Linux, FreeBSD and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable examples, utils, tests, and useroot for OHOS compat
        tc.project_options["examples"] = False
        tc.project_options["utils"] = False
        tc.project_options["tests"] = False
        tc.project_options["useroot"] = False
        tc.generate()

        # Set AR explicitly for meson's early archiver detection.
        # CI profile's buildenv PATH may not flow to the meson subprocess.
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/ar")
        envvars = env.vars(self)
        envvars.save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["fuse3"]
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs.extend(["dl", "rt"])
        elif self.settings.os in ("OHOS",):
            # dl/rt are part of libc on OHOS, no extra linking needed
            pass
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "fuse3")
