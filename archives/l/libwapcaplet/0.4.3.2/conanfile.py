#!/usr/bin/env python3
"""Conan recipe for libwapcaplet 0.4.3.2 (NetSurf string internment library).

libwapcaplet 是 NetSurf 浏览器组件库，上游使用 NetSurf 自有构建系统
（Makefile include $(NSSHARED)/makefiles/Makefile.tools），本平台无
netsurf-buildsystem 包。补丁 0001-Makefile.patch 将顶层 Makefile 替换为
standalone Makefile（保留原编译标志、去除 -Werror 以兼容 clang 15）。

构建：make && make install PREFIX=<package_folder>
测试：上游 `make check` 依赖 libcheck（test/testmain.c 直接 #include <check.h>），
本平台无 libcheck 包，探索阶段用自定义 standalone 测试程序 test_lwc.c 覆盖
核心 lwc_string_* API（24/24 PASS，见 notes.md）；test_package 以消费者视角
用 CMake 调用真实 API 验证（16 个断言）。

OHOS 陷阱（E120）：OHOS SDK 的 lld 链接 libxml2.so.16，需要把 SDK llvm 的
lib 目录注入 LD_LIBRARY_PATH，否则链接器无法启动。库本身是静态 .a，无需
ELF 签名/RPATH（R38 不适用，属库类型）。
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibwapcapletConan(ConanFile):
    name = "libwapcaplet"
    version = "0.4.3.2"
    description = "String internment and management tools (NetSurf project)"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libwapcaplet/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libwapcaplet 无运行时/编译依赖
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libwapcaplet is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # standalone Makefile builds in-source (objects next to sources)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm_libdir(self) -> str:
        """E120: 定位 SDK llvm 的 lib 目录（含 libxml2.so.16）。

        优先从编译器可执行文件解析（readlink 链 → llvm/bin 的父目录/lib），
        无法解析时回退到已知 SDK 路径，最后仍不存在则跳过（编译本身不依赖）。
        """
        # R33: tools.build:compiler_executables 是 dict conf（R33），
        # 必须整体读取后取 "c" 键，不能用子键语法 :c
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        candidate = None
        try:
            p = Path(cc)
            while p.is_symlink():
                p = Path(os.path.realpath(p))
            # .../llvm/bin/clang -> .../llvm/lib
            bin_dir = p.parent if p.parent.name == "bin" else None
            if bin_dir and (bin_dir.parent / "lib").is_dir():
                candidate = str(bin_dir.parent / "lib")
        except Exception:
            candidate = None
        if candidate is None:
            candidate = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(candidate):
            return candidate
        return ""

    def build(self):
        apply_conandata_patches(self)

        # E120: OHOS SDK lld 链接 libxml2.so.16，注入其 lib 目录到
        # LD_LIBRARY_PATH 使链接器可在 CI worker 上运行（SDK lib 路径
        # 不在默认 loader 搜索路径上）。
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            os.environ["LD_LIBRARY_PATH"] = sdk_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        # R33: 编译器/归档工具从 Conan conf 获取，禁止裸 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # R9: -j1 (HMDFS 上 make -j>1 jobserver mkfifo 报 EPERM, E074)
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1")

    def package(self):
        # standalone Makefile 的 install 目标遵循 PREFIX/DESTDIR
        self.run(f"make install PREFIX={self.package_folder}")

    def package_info(self):
        # 库文件为 libwapcaplet.a，lib 名是 "wapcaplet"（pkg-config -lwapcaplet）
        self.cpp_info.libs = ["wapcaplet"]
        self.cpp_info.set_property("cmake_file_name", "LibWapcaplet")
        self.cpp_info.set_property("cmake_target_name", "LibWapcaplet::wapcaplet")
        self.cpp_info.set_property("pkg_config_name", "libwapcaplet")
