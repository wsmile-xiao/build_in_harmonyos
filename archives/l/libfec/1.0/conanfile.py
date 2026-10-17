#!/usr/bin/env python3
"""Conan recipe — libfec 1.0 (Phil Karn's FEC library, autotools).

HarmonyOS adaptation:
- config.guess/config.sub upgraded + __OHOS__ detection (aarch64-unknown-linux-ohos)
- aarch64/arm64 MLIBS adds cpu_mode_arm64.o (portable C backend detection)
- REBIND empty on HarmonyOS (no ldconfig)
- makefile.in uses $(CC) (OHOS ships clang, no gcc) and install supports DESTDIR via cp
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class LibfecConan(ConanFile):
    name = "libfec"
    version = "1.0"
    description = "Forward error correction (FEC) library: Viterbi, Reed-Solomon, CCSDS, DSP primitives"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/quiet/libfec"
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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        if not self.options.shared:
            # 静态构建时仅保留 libfec.a，避免运行时动态加载解析到其他 libfec.so
            rm(self, "libfec.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["fec"]
