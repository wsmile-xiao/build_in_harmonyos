#!/usr/bin/env python3
"""Conan recipe for stm32flash 0.7."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Stm32flashConan(ConanFile):
    name = "stm32flash"
    version = "0.7"
    description = "Flash STM32 devices through the built-in serial bootloader"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/stm32flash/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("stm32flash requires Linux or OHOS serial APIs")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "clang")
        archiver = compilers.get("ar", "ar")
        cflags = "-O2 -DNDEBUG -fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        self.run(
            f'make -j1 CC="{compiler}" AR="{archiver}" '
            f'CFLAGS="{cflags}" LDFLAGS="{ldflags}"'
        )

    def package(self):
        copy(
            self,
            "stm32flash",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "stm32flash.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "gpl-2.0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        binary = os.path.join(self.package_folder, "bin", "stm32flash")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(objcopy):
            signed = binary + ".signed"
            self.run(f'"{objcopy}" --remove-section .codesign "{binary}"', quiet=True)
            self.run(
                f'"{sign_tool}" sign -inFile "{binary}" -outFile "{signed}" -selfSign 1',
                quiet=True,
            )
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
