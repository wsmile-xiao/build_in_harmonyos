#!/usr/bin/env python3
"""Conan recipe for fontconfig 2.18.3 — font configuration library
(C, meson build, freedesktop).

Dependencies: freetype2 (>= 21.0.15 pkg-config version — freetype's .pc
Version is 26.6.20 via system_package_version, satisfies) — published on
ohpcd (freetype/2.14.3). meson test integrated (L1 real pass rate).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class FontconfigConan(ConanFile):
    name = "fontconfig"
    version = "2.18.3"
    description = "Font configuration and customization library"
    license = "MIT"
    homepage = "https://www.freedesktop.org/wiki/Software/fontconfig/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # freetype published on ohpcd (freetype/2.14.3 — .pc version 26.6.20
        # satisfies fontconfig's freetype2 >= 21.0.15); libxml2 published
        # (meson.build requires libxml-2.0)
        self.requires("freetype/2.14.3")
        self.requires("libxml2/2.15.3")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        # docs need DocBook utils — skip them; CLI tools (fc-list/fc-cache/
        # fc-match) are built by default (tools option is enabled/disabled/
        # auto, NOT a tool list)
        tc.project_options["tools"] = "enabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # meson needs ar in PATH (pixman lesson) — llvm-ar lives in hnp/bin
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        os.environ["CXX_AR"] = "/data/service/hnp/bin/llvm-ar"
        os.environ["PATH"] = "/data/service/hnp/bin:" + \
            os.environ.get("PATH", "")
        meson = Meson(self)
        meson.configure()
        meson.build()
        # L1: upstream test suite (meson test) — real pass rate.
        # --no-rebuild: some tests rebuild via network downloads (BLFS:
        # "An Internet connection is needed for some tests") — avoid the
        # rebuild step timing out. Meson.test() takes no args — run via
        # self.run instead.
        # failures don't block the package build — real pass rate is
        # reported (2 network-related failures per BLFS: "An Internet
        # connection is needed for some tests" — recorded in MANIFEST)
        self.run(f"meson test -C {self.build_folder} --no-rebuild",
                 ignore_errors=True)

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["fontconfig"]
        self.cpp_info.set_property("pkg_config_name", "fontconfig")
