#!/usr/bin/env python3
"""
Conan recipe for c-periphery v1.0.0 - OHOS (OpenHarmony) aarch64 adaptation.

Native GNU Makefile static library (periphery.a), zero external dependencies.
Portability patch: OHOS NDK struct termios member names (__c_ispeed/__c_ospeed).
No install target upstream -> package() copies periphery.a + src/*.h manually.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CPeripheryConan(ConanFile):
    name = "c-periphery"
    version = "1.0.0"
    description = "C library for peripheral I/O (GPIO, I2C, MMIO, SPI, Serial) on Linux"
    license = "MIT"
    homepage = "https://github.com/vsergeev/c-periphery"
    url = "https://github.com/vsergeev/c-periphery"
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
        # Explicit filename: the codeload source URL does not end in .tar.gz,
        # so conan tools.files.get() cannot infer the tar.gz format from the
        # URL alone (it would default to zip and fail with BadZipFile).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="c-periphery-1.0.0.tar.gz")

    def validate(self):
        if self.options.shared:
            self.output.warning(
                "c-periphery v1.0.0 provides only a static library (periphery.a); "
                "the shared option has no effect"
            )

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from the Conan conf, never from shell env vars.
        # The registered conf is the dict "tools.build:compiler_executables"
        # (set by ci/conan/profiles/ohos-aarch64 as {"c": ..., "cpp": ...});
        # per-language ":c"/":ar" are not standalone conf names in Conan 2.x.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        # v1.0.0 has no install target and only builds the static library.
        # Cache flow: build dir != source dir; the Makefile lives in the
        # source folder, so target it explicitly.
        self.run(f"make -C {self.source_folder} CC={cc} AR={ar} -j1")
        # Compile (do NOT run) the upstream test binaries to prove the full
        # upstream test closure builds on OHOS. The tests themselves require
        # real hardware (GPIO/I2C/MMIO/serial/SPI) + interactive stdin, so
        # they cannot be executed on a hardware-less build machine; see
        # notes.md and test_package/MANIFEST.yml for the full disclosure.
        self.run(f"make -C {self.source_folder} CC={cc} AR={ar} tests -j1")

    def package(self):
        # Upstream ships headers in src/ alongside the sources.
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        # Upstream names the static archive "periphery.a" (no "lib" prefix);
        # rename to the canonical "libperiphery.a" so downstream find_library
        # (CMake/CPack) and cpp_info.libs=["periphery"] resolve correctly.
        copy(self, "periphery.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        src = os.path.join(self.package_folder, "lib", "periphery.a")
        dst = os.path.join(self.package_folder, "lib", "libperiphery.a")
        os.rename(src, dst)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["periphery"]
