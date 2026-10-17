#!/usr/bin/env python3
"""Kamailio-lua 6.0.6 test_package —— Conan L1 消费者测试（OHOS PC）。

被测产物是 kamailio 运行期 dlopen 的插件（app_lua.so），不是可链接库，
L1 测试围绕「产物结构 + 目标平台（鸿蒙）ABI 契约 + 动态加载器实测」展开：

  test_app_lua_ohos.sh
    [1]  产物存在性
    [H1] OHOS ABI 契约        ELF64 / AArch64 / ET_DYN        （鸿蒙特有）
    [H2] OHOS 依赖自洽        NEEDED 含 libc.so；无 liblua.so （鸿蒙特有）
    [H3] RPATH 卫生           无 RPATH/RUNPATH
    [H4] kamailio 模块接口    mod_register + _app_lua_exports
    [H5] 内嵌 Lua 运行时      luaL_newstate/luaL_openlibs + "Lua 5.4"
    [H7] 模块目标标识        aarch64/linux（与 OHOS 上 core 口径一致）  （鸿蒙特有）
    [H8] 编译标志集合一致    无 USE_SCTP / HAVE_RESOLV_RES（同 core 口径） （鸿蒙特有）
  dlopen_probe.c
    [H6] OHOS 加载器实测      真实 dlopen（鸿蒙特有）
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class KamailioLuaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 生成物（env 脚本、编译的探针）落到 build/，保持 test_package 源码目录干净
        self.folders.build = "build"
        self.folders.generators = os.path.join("build", "generators")

    def test(self):
        pkg = self.dependencies["kamailio-lua"].package_folder
        tp = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(tp, "test_app_lua_ohos.sh")
        probe_src = os.path.join(tp, "dlopen_probe.c")

        # 结构 + ABI + 符号检查（含鸿蒙特有 [H1]/[H2]）
        self.run(f'/bin/sh "{script}" "{pkg}"')

        if cross_building(self):
            self.output.info("cross-building：跳过 [H6] 运行期 dlopen 实测")
            return

        # [H6] OHOS 动态加载器实测（鸿蒙特有）
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        probe = os.path.join(self.build_folder, "dlopen_probe")
        self.run(f'{cc} -O1 -o "{probe}" "{probe_src}"')
        module = os.path.join(pkg, "lib", "kamailio", "app_lua.so")
        self.run(f'"{probe}" "{module}"')
