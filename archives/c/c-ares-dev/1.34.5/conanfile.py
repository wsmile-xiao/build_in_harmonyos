#!/usr/bin/env python3
"""Conan recipe for c-ares 1.34.5 — Autotools project (configure + make).

Based on the verified 1.34.6 recipe. All three platform patches are compatible
with 1.34.5 (dry-run verified).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CaresConan(ConanFile):
    name = "c-ares-dev"
    version = "1.34.5"
    description = "C library for asynchronous DNS requests"
    license = "MIT"
    homepage = "https://c-ares.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # HarmonyOS: use lld linker (no GNU ld available on OHOS)
        tc.extra_ldflags.append("-fuse-ld=lld")
        tc.configure_args.append("LD=ld.lld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Ensure CONFIG_SHELL exists on CI worker (profile may point to non-existent path)
        import os
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        os.environ["LD"] = "ld.lld"
        autotools.configure()
        autotools.make(args=["-j1"])
        # ── 上游官方测试 (R28) ──
        # c-ares 上游测试需要 Google Test/Mock (GMOCK_LIBS)
        # CI worker 和 Conan 制品仓(ohpcd)均无 gtest/gmock
        # make check 会因缺少 gtest 编译失败，产生具体错误证据
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["cares"]
        self.cpp_info.set_property("cmake_file_name", "c-ares")
        self.cpp_info.set_property("cmake_target_name", "c-ares::c-ares")
        self.cpp_info.set_property("pkg_config_name", "libcares")
