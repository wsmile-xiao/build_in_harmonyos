#!/usr/bin/env python3
"""Conan recipe for flashrom 1.6.0.

flashrom is a utility for identifying, reading, writing, verifying and erasing
flash chips. This recipe builds flashrom with the dummy programmer enabled,
which requires no external hardware dependencies.

The library libflashrom is the primary Conan artifact; the flashrom CLI binary
is also installed.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class FlashromConan(ConanFile):
    name = "flashrom"
    version = "1.6.0"
    description = "Utility for identifying, reading, writing, verifying and erasing flash chips"
    license = "GPL-2.0-only"
    homepage = "https://flashrom.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: Use `in` for os check, not `==`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"flashrom is only supported on Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System-name libraries default to static
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Set archiver path (HarmonyOS doesn't have llvm-ar in default PATH)
        tc.ar = "/data/service/hnp/bin/llvm-ar"
        tc.strip = "/data/service/hnp/bin/llvm-strip"
        # Build only the dummy programmer (no external hardware dependencies)
        tc.project_options["programmer"] = "dummy"
        # Disable optional features that require unavailable dependencies
        tc.project_options["rpmc"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["classic_cli"] = "enabled"
        tc.project_options["documentation"] = "disabled"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["flashrom"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin", "sbin"]
