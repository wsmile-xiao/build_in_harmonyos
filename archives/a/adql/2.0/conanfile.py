#!/usr/bin/env python3
"""Conan recipe for adql 2 (libadql — ADQL 2.0 parser) on HarmonyOS PC.

真实构建模式：依赖制品仓 boost/1.90.0（完整头文件树版，含 spirit 及
其依赖 fusion/variant/phoenix——ccapi 等库实证可用），waf configure
的 Boost 检查真实通过，真实构建 + test_package 真实解析 ADQL 查询。
"""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class AdqlConan(ConanFile):
    name = "adql"
    version = "2.0"
    description = "libadql — C++ parser for IVOA ADQL 2.0 queries"
    license = "GPL-2.0"
    homepage = "https://github.com/Caltech-IPAC/libadql"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libadql 的 wscript configure 通过 ctx.check_cxx 检查 Boost
        # (boost/spirit/include/qi.hpp + 链接 boost_system)。
        # 制品仓 boost/1.90.0 为完整头文件树版（含 spirit/fusion/variant/
        # phoenix 等 header-only 库——ccapi 7.10.1 实证可用），无需额外
        # overlay；boost/1.90.0.1.1 为 minimal 组件集不含 spirit。
        self.requires("boost/1.90.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_env(self):
        # OHOS 编译器（clang/clang++）位于 /data/service/hnp/bin/，不在默认 PATH 中。
        # waf 的 compiler_cxx 模块只探测 clang++/g++，找不到编译器即 configure 失败。
        # 参照仓库内 jack/1.9.22 先例，从 conan conf 读取编译器可执行文件路径并导出。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        return env

    def build(self):
        # OHOS 制品仓 boost 为 header-only 版（无编译的 libboost_system/
        # libboost_thread——boost_system 1.66+ 本就 header-only）：wscript
        # 的 check_cxx 会链接 -lboost_system 导致 "Checking for Boost: no"。
        # 直接改 wscript：注入 BOOST_ERROR_CODE_HEADER_ONLY 宏 + Boost 检查
        # 改纯编译（去掉 libpath/rpath/lib 链接参数）——真实检查 qi.hpp
        # 可编译，无需链接不存在的库（catdoc 同款 python 替换，避 patch
        # 文件格式问题）。
        ws = os.path.join(self.source_folder, "wscript")
        with open(ws, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace(
            "        boost_libs=['boost_system','boost_thread']",
            "        boost_libs=['boost_system','boost_thread']\n"
            "    # OHOS 制品仓 boost header-only 版（无 libboost_system）——\n"
            "    # 注入宏（boost_system 1.66+ 本就 header-only），检查纯编译。\n"
            "    ctx.env.append_value('CXXFLAGS', '-DBOOST_ERROR_CODE_HEADER_ONLY')",
        )
        s = s.replace(
            "                  includes=[boost_inc], uselib_store='boost',\n"
            "                  libpath=[ctx.options.boost_libdir],\n"
            "                  rpath=[ctx.options.boost_libdir],\n"
            "                  lib=boost_libs)",
            "                  includes=[boost_inc], uselib_store='boost')",
        )
        with open(ws, "w", encoding="utf-8") as f:
            f.write(s)
        # 上游使用 waf 构建系统。libadql 源码树中的 waf 脚本文件名是
        # waf-1.7.9 / waf-2.0.23（不带版本号的可执行文件并不存在），
        # 选用 waf-2.0.23，用 python3 显式调用（CI 环境的 python 解释器）。
        python = "python3"
        boost_pkg = self.dependencies["boost"].package_folder
        boost_dir = os.path.join(boost_pkg, "include", "boost")
        with self._compiler_env().vars(self).apply():
            self.run(
                f'"{python}" waf-2.0.23 configure '
                f'--prefix="{self.package_folder}" '
                f'--boost-dir="{boost_pkg}" '
                f'--boost-incdir="{os.path.dirname(boost_dir)}" '
                f'--boost-libdir="{os.path.join(boost_pkg, "lib")}" '
                "--boost-libs=boost_system",
                cwd=self.source_folder,
            )
            self.run(f'"{python}" waf-2.0.23 build', cwd=self.source_folder)
            self.run(f'"{python}" waf-2.0.23 install', cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["adql"]
        self.cpp_info.includedirs = ["include"]
