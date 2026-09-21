#!/usr/bin/env python3
"""Conan recipe — sili 0.3.0 (single-header C99 library, Makefile-driven).

sili is a collection of cross-platform single-header libraries for modern
C99/C11 and C++20 (sili.h + sifig.h). The upstream Makefile compiles the
single-header implementation (`-D SI_IMPLEMENTATION -c sili.h`) into a
static library `libsili.a`. Consumers include `sili.h` and link `libsili.a`,
or define SI_IMPLEMENTATION in exactly one translation unit.

Official source: EimaMei/sili tag v0.3.0 (codeload official tarball).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class SiliConan(ConanFile):
    name = "sili"
    version = "0.3.0"
    description = "A general-purpose single-header C99/C++20 library, an alternative to C/C++ standard libraries"
    license = "zlib"  # LICENSE is zlib-style
    homepage = "https://github.com/EimaMei/sili"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("single-header", "c99", "strings", "containers", "unicode")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility — use `in ("Linux", "OHOS")`
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # codeload 响应 Content-Type 与 URL basename 均无 .tar.gz 后缀，需显式
        # filename 让 unzip 按 .tar.gz 识别（否则被误判为 zip 抛 BadZipFile，
        # 知识条目 E276，drwav 同仓先例）。
        src = dict(self.conan_data["sources"])
        src["filename"] = "sili-0.3.0.tar.gz"
        get(self, **src, strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Upstream Makefile static target: compile single header to .o, archive.
        # We replicate it explicitly so OHOS cross flags from the toolchain env apply.
        build_dir = os.path.join(self.source_folder, "build")
        os.makedirs(build_dir, exist_ok=True)
        self.run(
            f'{cc} -O3 -std=c99 -fPIC -x c -D SI_IMPLEMENTATION '
            f'-c sili.h -o {os.path.join(build_dir, "sili.o")}',
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            f'llvm-ar rcs {os.path.join(build_dir, "libsili.a")} '
            f'{os.path.join(build_dir, "sili.o")}',
            cwd=self.source_folder,
            env="conanbuild",
        )
        # 注：llvm-ar 由 OHOS profile buildenv PATH（/data/service/hnp/bin、
        # $HOME/usr/local/bin）提供，与 GnuToolchain conanbuild 环境一致。

    def package(self):
        copy(self, "sili.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "sifig.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libsili.a", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["sili"]
