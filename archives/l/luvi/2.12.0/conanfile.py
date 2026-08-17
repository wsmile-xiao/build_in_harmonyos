#!/usr/bin/env python3
"""Conan recipe — luvi v2.12.0 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

luvi 是 luvit 的 C 运行时骨架（LuaJIT + libuv + luv 绑定聚合）。
deps 全为 git 子模块（tar.gz 不含子模块内容），source() 中按仓库
lua-luv 1.51.0-1 先例的版本分别拉取 luv/libuv/LuaJIT/lua-compat-5.3。

构建要点（本地已验证）：
- libuv 应用仓库 libuv/1.52.1 的 OHOS 补丁（排除 sched_getaffinity/mmsg）
- VERSION 文件（避免 CMake 走 git describe，tar.gz 无 .git）
- luajit_relver.txt 手动生成（LuaJIT CMake 用 git 生成，无 .git 会失败）
- CMake 加 -D_GNU_SOURCE（libuv 需 _GNU_SOURCE 编译 core.c）
- 关闭可选模块（OpenSSL/PCRE/LPEG/ZLIB），仅核心 luvi 可执行文件
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuviConan(ConanFile):
    name = "luvi"
    version = "2.12.0"
    description = "A multi-platform asynchro IO, and HTTP Server framework"
    license = "Apache-2.0"
    homepage = "https://github.com/luvit/luvi"
    url = "https://github.com/luvit/luvi"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 拉取子模块（luvi 的 deps 是 git 子模块，tar.gz 不含）
        self._fetch_submodule("luv", "deps/luv")
        self._fetch_submodule("libuv", "deps/luv/deps/libuv")
        self._fetch_submodule("luajit", "deps/luv/deps/luajit")
        self._fetch_submodule("lua-compat-5.3", "deps/luv/deps/lua-compat-5.3")
        # VERSION 文件：避免 CMake 走 git describe（tar.gz 无 .git）
        with open(os.path.join(self.source_folder, "VERSION"), "w") as f:
            f.write("v2.12.0\n")

    def _fetch_submodule(self, key, dest_rel):
        sub = self.conan_data["submodules"][key]
        dest = os.path.join(self.source_folder, dest_rel)
        os.makedirs(dest, exist_ok=True)
        # get() 的 destination 是解压目标目录；strip_root=False 保留 tar 内
        # 顶层目录，解压后为 _subtmp/<顶层目录>/...。固定 commit 的 codeload
        # 归档顶层目录名含 commit SHA（如 LuaJIT-1edc3e5...），故动态匹配。
        get(self, url=sub["url"], sha256=sub["sha256"],
            filename=sub["filename"],
            destination=os.path.join(self.source_folder, "_subtmp"),
            strip_root=False)
        subtmp = os.path.join(self.source_folder, "_subtmp")
        entries = [e for e in os.listdir(subtmp)
                   if os.path.isdir(os.path.join(subtmp, e))]
        if len(entries) != 1:
            raise ConanException(
                f"submodule {key}: expected 1 top dir under _subtmp, got {entries}")
        src = os.path.join(subtmp, entries[0])
        for item in os.listdir(src):
            shutil.move(os.path.join(src, item), os.path.join(dest, item))
        shutil.rmtree(subtmp, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WithOpenSSL"] = "OFF"
        tc.variables["WithPCRE"] = "OFF"
        tc.variables["WithLPEG"] = "OFF"
        tc.variables["WithZLIB"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_C_FLAGS"] = "-D_GNU_SOURCE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # LuaJIT 的 luajit_relver.txt 由 CMake 用 git 生成（tar.gz 无 .git 会失败）
        relver = os.path.join(
            self.source_folder, "deps", "luv", "deps", "luajit", "src", "luajit_relver.txt")
        if not os.path.isfile(relver):
            with open(relver, "w") as f:
                f.write("1700000000\n")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        binary = os.path.join(self.build_folder, "luvi")
        if os.path.isfile(binary):
            copy(self, "luvi", src=os.path.dirname(binary),
                 dst=os.path.join(self.package_folder, "bin"))
        else:
            raise ConanException("luvi binary not built")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
