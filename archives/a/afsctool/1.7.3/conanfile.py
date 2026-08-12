#!/usr/bin/env python3
"""Conan recipe for afsctool 1.7.3 — HFS+/APFS/ZFS compressed-file utility.

afsctool 是 C + C++ 命令行工具（afsctool/zfsctool 两个可执行），CMake 构建。
依赖：
- zlib（FindZLIBP：pkg-config zlib 或 fallback FindZLIB）→ zlib/1.3.1
- Google sparsehash（header-only，FindSPARSEHASH 用 pkg-config REQUIRED，
  但 sparsehash 包无 .pc → 补丁 0001 改 find_path 兜底）→ sparsehash/2.0.4
- fts（musl 无 fts.h → musl-fts 提供 libfts.a + fts.h）→ musl-fts/1.2.7
可绕过：lzfse 子模块仅 Apple 启用（CMakeLists if(APPLE)），OHOS 不需要；
libbsd 未发布制品仓，补丁 0002/0003 移除 <bsd/stdlib.h> include 与 -lbsd 链接
（musl string.h 自带 strlcpy）。
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


def _sdk_llvm_libdir():
    """OHOS SDK 的 llvm/lib 目录（含正确的 libxml2.so.16）。

    OHOS SDK 的 lld（llvm/bin/lld）动态依赖 libxml2.so.16，但其默认
    LD_LIBRARY_PATH 不含 SDK llvm/lib，CI worker 上 lld 加载
    libxml2.so.16 失败（xmlFreeDoc symbol not found）→ CMake 编译器
    检测失败。此函数 glob 定位 SDK llvm/lib 目录，供 build() 注入
    LD_LIBRARY_PATH，保证 lld 加载到 SDK 自带符号齐全的 libxml2。
    """
    for root in ("/data/service/hnp", "/usr"):
        for f in glob.glob(os.path.join(root, "**", "ohos-sdk*", "ohos", "native", "llvm", "lib", "libxml2.so.16"), recursive=True):
            return os.path.dirname(f)
    return None


class AfsctoolConan(ConanFile):
    name = "afsctool"
    version = "1.7.3"
    description = "Utility for manipulating HFS+/APFS and ZFS compressed files"
    license = "GPL-3.0"
    homepage = "https://github.com/RJVB/afsctool"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("sparsehash/2.0.4")
        self.requires("musl-fts/1.2.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # URL 无 .tar.gz 扩展名（codeload /tar.gz/ 路径），需 filename 指定以便 conan 正确解压
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="afsctool-1.7.3.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # FindZLIBP 优先 pkg-config，conan zlib 包提供 zlib.pc；sparsehash/fts
        # 的 include 通过 CMAKE_PREFIX_PATH 供 find_path 搜索（补丁 0001/0002）
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS SDK lld 动态依赖 libxml2.so.16，默认 LD_LIBRARY_PATH 不含
        # SDK llvm/lib → CI worker 上 lld 加载失败（xmlFreeDoc symbol not
        # found），CMake 编译器检测崩溃。构建前注入 SDK llvm/lib 目录，
        # 让 lld 加载到 SDK 自带符号齐全的 libxml2（环境兼容，R33）。
        sdk_llvm = _sdk_llvm_libdir()
        if sdk_llvm:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = sdk_llvm + ((":" + old) if old else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 上游 CMakeLists 仅 Apple 分支 install；非 Apple 手动拷贝两个可执行
        # （cmake_layout 下二进制在 build_folder=build/Release）
        bin_dir = self.build_folder
        for exe in ("afsctool", "zfsctool"):
            src = os.path.join(bin_dir, exe)
            if os.path.exists(src):
                copy(self, exe, src=bin_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # musl-fts 默认 shared（libfts.so.0），传递其运行时 lib 路径，
        # 保证下游/消费测试执行 afsctool 时能加载 libfts
        fts = self.dependencies.get("musl-fts")
        if fts and fts.options.shared:
            fts_libdir = os.path.join(fts.package_folder, fts.cpp_info.libdirs[0])
            self.runenv_info.append_path("LD_LIBRARY_PATH", fts_libdir)
