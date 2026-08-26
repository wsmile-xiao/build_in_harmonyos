#!/usr/bin/env python3
"""Conan recipe for umka-lang 1.5.5 — Makefile-based build.

umka-lang uses a plain Makefile (not autotools). The Makefile detects
the platform via `uname -s`, which returns "HarmonyOS" on OpenHarmony.
We override PLATFORM=Linux to select the correct build flags.

Build products:
  - bin/umka        (command-line interpreter)
  - lib/libumka.a   (static library)
  - lib/libumka.so  (shared library)
  - include/umka_api.h (C embedding API header)

R33: Compiler path is injected via VirtualBuildEnv from the Conan profile,
not from undefined shell env vars.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class UmkaLangConan(ConanFile):
    name = "umka-lang"
    version = "1.5.5"
    description = "Umka: a statically typed embeddable scripting language"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vtereshkov/umka-lang"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Generate build env from Conan profile (CC, CXX, etc.)
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # umka-lang uses a plain Makefile (not autotools)
        # PLATFORM=Linux for HarmonyOS compatibility (uname -s returns "HarmonyOS")
        # VirtualBuildEnv injects CC from the Conan profile
        # LDFLAGS override: -fuse-ld=ld avoids OHOS SDK's lld which has a
        # broken libxml2.so.16 dependency in CI environment
        self.run('make -j1 PLATFORM=Linux LDFLAGS="-lm -ldl -fuse-ld=ld"',
                 cwd=self.source_folder)

    def package(self):
        # Install to Conan package folder
        self.run(f'make install PLATFORM=Linux LDFLAGS="-lm -ldl -fuse-ld=ld" PREFIX={self.package_folder}',
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["umka"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
