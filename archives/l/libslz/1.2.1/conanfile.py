#!/usr/bin/env python3
"""Conan recipe — libslz 1.2.1 (SLZ, StateLess Zip).

Build system: 裸 Makefile（无 configure），零第三方依赖。

设备/CI 实测要点（详见 notes.md）：
  * 上游 Makefile `CC := $(CROSS_COMPILE)gcc`，设备与 CI worker 均无 gcc →
    必须在 make 命令行覆盖 CC/AR；R33：编译器从 conan conf 取，禁止读环境变量。
  * CFLAGS 在 make 命令行钉死（先例：CFLAGS 环境泄漏致 Segv），上游默认值原样保留。
  * 不走 `make install`：install-tools 目标执行 `$(STRIP) zenc`，HarmonyOS 下 strip
    使 .codesign 失效报 EPERM（先例 integrit/E703）→ package() 直接复制产物。
  * `tools` 目标恒定构建：包内交付 zenc/zdec 可执行文件（R38 → 软件级 commands.json）。
"""
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


class LibslzConan(ConanFile):
    name = "libslz"
    version = "1.2.1"
    description = "SLZ (StateLess Zip) — fast memory-less gzip/zlib/deflate stream compressor"
    license = "MIT"
    homepage = "https://github.com/wtarreau/libslz"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libslz is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器来自 conf（整体取 dict 再索引，点分子键写法在 Conan 2.x 抛异常）
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c") or "clang"
        ar = comp.get("ar") or "llvm-ar"

        # R9：make -j1；CFLAGS 显式钉死（上游 Makefile 默认 -O3 -fomit-frame-pointer -Wall -g，
        # 其 `-I$(TOPDIR)/include` 指向上游并不提供的目录，源文件同目录引号包含已足够）
        cflags = "-O3 -fomit-frame-pointer -Wall -g"
        common = f'make -j1 CC="{cc}" AR="{ar}" CFLAGS="{cflags}"'

        # 静态库 + 命令行工具（zenc/zdec）
        self.run(f"{common} static tools", cwd=self.source_folder)
        if self.options.shared:
            self.run(f"{common} shared", cwd=self.source_folder)

    def package(self):
        # 头文件
        copy(self, "slz.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        # 许可证
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # 库产物（按选项二选一；不走 make install，见 docstring）
        lib_dst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libslz.so*", src=self.source_folder,
                 dst=lib_dst, keep_path=False)
        else:
            copy(self, "libslz.a", src=self.source_folder,
                 dst=lib_dst, keep_path=False)

        # 命令行工具（R38 → 软件级 commands.json 已声明）
        bin_dst = os.path.join(self.package_folder, "bin")
        copy(self, "zenc", src=self.source_folder, dst=bin_dst, keep_path=False)
        copy(self, "zdec", src=self.source_folder, dst=bin_dst, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["slz"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
