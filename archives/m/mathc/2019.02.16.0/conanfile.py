#!/usr/bin/env python3
"""Conan recipe — mathc 2019.02.16.0 (pure C99 math library, no build system).

mathc is a single-translation-unit C99 math library (mathc.c + mathc.h)
providing 2D/3D/4D vectors, quaternions, matrices and easing functions.
The official tag ships no Makefile/CMake/configure script, so the recipe
compiles mathc.c directly with the toolchain compiler (R33: compiler comes
from Conan conf, never bare shell env vars) and archives libmathc.a.
Consumers include mathc.h and link libmathc.a.

Official source: felselva/mathc tag v2019.02.16.0 (GitHub official tarball).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class MathcConan(ConanFile):
    name = "mathc"
    version = "2019.02.16.0"
    description = "A simple math library for 2D and 3D programming (vectors, quaternions, matrices, easing functions)"
    license = "MIT"
    homepage = "https://github.com/felselva/mathc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("math", "vector", "matrix", "quaternion", "c99")

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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        build_dir = os.path.join(self.source_folder, "build")
        os.makedirs(build_dir, exist_ok=True)
        self.run(
            f'{cc} -O2 -std=c99 -fPIC -c mathc.c '
            f'-o {os.path.join(build_dir, "mathc.o")}',
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            f'llvm-ar rcs {os.path.join(build_dir, "libmathc.a")} '
            f'{os.path.join(build_dir, "mathc.o")}',
            cwd=self.source_folder,
            env="conanbuild",
        )
        # 注：llvm-ar 由 OHOS profile buildenv PATH（/data/service/hnp/bin、
        # $HOME/usr/local/bin）提供，与 GnuToolchain conanbuild 环境一致。

    def package(self):
        copy(self, "mathc.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libmathc.a", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["mathc"]
        # mathc.h 公开 API 使用 sqrtf/sinf/cosf 等（math.h），消费者需链接 libm
        self.cpp_info.system_libs = ["m"]
