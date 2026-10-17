#!/usr/bin/env python3
"""Conan recipe for quickjs 2024-01-13 — Fast, small, and embeddable JavaScript engine.

QuickJS is a small and embeddable JavaScript engine.
Build system: Makefile
License: MIT

R26: Must build static only.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class QuickjsConan(ConanFile):
    name = "quickjs"
    version = "2024-01-13"
    description = "Fast, small, and embeddable JavaScript engine"
    license = "MIT"
    homepage = "https://bellard.org/quickjs/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."
        self.folders.build = "_build"
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration(
                "OHOS 构建需要 tools.build:compiler_executables.c"
            )
        cc = cc or "clang"
        ar = compilers.get("ar") or os.path.join(os.path.dirname(cc), "llvm-ar")
        host_cc = compilers.get("c_host") or "gcc"
        args = [
            f'CC="{cc}"',
            f'HOST_CC="{host_cc}"',
            f'AR="{ar}"',
            "CONFIG_BIGNUM=y",
            "-j2",
        ]
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        with env.vars(self).apply():
            self.run(
                "make {}".format(" ".join(args)),
                cwd=self.source_folder,
            )

    def package(self):
        copy(self, "*.h",
             self.source_folder,
             os.path.join(self.package_folder, "include", "quickjs"))
        copy(self, "libquickjs.a",
             self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "qjs",
             self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "qjsc",
             self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE",
             self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        # 校验关键产物已成功打包：copy() 在源文件不存在时只返回空列表，
        # 需主动检查目标路径，避免制品包不完整却被静默成功。
        expected_artifacts = [
            os.path.join(self.package_folder, "lib", "libquickjs.a"),
            os.path.join(self.package_folder, "bin", "qjs"),
            os.path.join(self.package_folder, "bin", "qjsc"),
            os.path.join(self.package_folder, "licenses", "LICENSE"),
        ]
        for artifact in expected_artifacts:
            if not os.path.exists(artifact):
                raise ConanException(
                    f"package() 校验失败：未找到预期产物 {artifact}，"
                    f"请检查 build() 是否成功产出该文件"
                )

    def package_info(self):
        self.cpp_info.libs = ["quickjs"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
