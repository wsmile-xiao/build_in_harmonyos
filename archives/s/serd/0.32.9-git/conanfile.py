#!/usr/bin/env python3
"""Conan recipe for serd 0.32.9-git — Meson build system.

Serd is a lightweight C library for RDF syntax (Turtle/N-Triples/N-Quads)
parsing and serialization, used by the LV2 audio plugin ecosystem.
"""
import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SerdConan(ConanFile):
    name = "serd"
    version = "0.32.9-git"
    description = "Lightweight C library for RDF syntax parsing and serialization"
    license = "ISC"
    homepage = "https://drobilla.net/software/serd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"serd is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # serd 依赖 zix（portability/data structure 库）
        self.requires("zix/0.8.1-git")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["docs"] = "disabled"
        tc.project_options["html"] = "disabled"
        tc.project_options["man"] = "disabled"
        tc.project_options["tests"] = "enabled"
        tc.generate()
        # OHOS: meson cannot find llvm-ar via PATH, inject into native file
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc ="
        )
        with open(native_file, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试：meson test（serd 单元测试 + serdi 数据/IO 测试）
        # 注意：self.run 的 cwd 已在 build-release 目录，直接 meson test
        #（不能用 -C build-release，会重复路径）
        self.run("meson test", env="conanbuild")

    def package(self):
        meson = Meson(self)
        meson.install()
        # 修正 serd-0.pc 的 prefix：meson install 生成 prefix=/（根目录），
        # 导致下游（sord）用 pkg-config 拿到 /include/serd-0 等不存在路径，
        # 头文件找不到。改写为包真实路径。
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "serd-0.pc")
        if os.path.isfile(pc_path):
            with open(pc_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "prefix=/",
                f"prefix={self.package_folder}",
            )
            with open(pc_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("Patched serd-0.pc prefix to package folder")

    def package_info(self):
        self.cpp_info.libs = ["serd-0"]
        self.cpp_info.includedirs = ["include/serd-0"]
        self.cpp_info.set_property("cmake_file_name", "serd")
        self.cpp_info.set_property("pkg_config_name", "serd-0")
