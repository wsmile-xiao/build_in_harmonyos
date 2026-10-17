#!/usr/bin/env python3
"""Conan recipe: kamailio-lua 6.0.6 (kamailio app_lua 模块) for HarmonyOS PC.

目标库 `kamailio-lua` 是发行版二进制子包名（Alpine `lua` 子包 / Debian
`kamailio-lua-modules`），对应上游工程 Kamailio SIP Server 6.0.6 中的
`src/modules/app_lua`（产物 `app_lua.so`，Lua 脚本支持）。

OHOS 平台要点（本配方的最小适配面）：
  * OHOS 既无系统 liblua、也无 lua 的 pkg-config 文件；Lua 由 Conan 依赖
    `lua/5.4.8.1` 提供，通过上游模块 Makefile 自身支持的 `LOCALBASE` 变量
    显式注入头文件/库路径（上游 Makefile 的第 3 条回退分支）。
  * `PKG_CONFIG_LIBDIR` 指向一个空目录，保证不会误用宿主机的 lua 探测结果。
  * kamailio 的 OS 探测基于 `uname -s`（OHOS 上是 `HarmonyOS`，无专属分支）；
    app_lua 模块源码不含任何平台条件编译（实测 `__OS_*`/`HAVE_*` 命中为 0），
    因此不引入平台补丁、不改上游源码，沿用上游 make 体系即可编译。
  * 只构建目标模块：`make modules modules=modules/app_lua`，无需先构建 core。
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KamailioLuaConan(ConanFile):
    name = "kamailio-lua"
    version = "6.0.6"
    description = (
        "Kamailio (SIP server) app_lua module - embedded Lua scripting support "
        "for HarmonyOS PC"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 产物是 kamailio 运行期 dlopen 的共享对象（插件），不声明 shared 选项
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一强制第三方依赖（上游 README 2.2 / CMakeLists.txt find_package(Lua REQUIRED)）
        self.requires("lua/5.4.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return tools.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        lua_prefix = self.dependencies["lua"].package_folder
        cc = self._cc()

        # 空 pkg-config 搜索目录：OHOS 无系统 lua，避免宿主探测结果串入
        # （GNU make 会把命令行变量导出到 recipe 的 shell 环境，故 pkg-config 可见）
        empty_pc = os.path.join(self.build_folder, "empty-pkgconfig")
        os.makedirs(empty_pc, exist_ok=True)

        vars_ = (
            f'LOCALBASE="{lua_prefix}" '
            f'PKG_CONFIG_LIBDIR="{empty_pc}" '
            f'CC="{cc}" LD="{cc}" '
            # OHOS 上 kamailio 无 harmonyos 专属分支，core 必须按 Linux ABI 构建；
            # 且 core 在 OHOS 上必须关闭 SCTP（sysroot 无 netinet/sctp.h）、
            # 去除 -DHAVE_RESOLV_RES（OHOS libc 无 _res）。
            # kamailio 加载模块时会校验 目标标识(arch/os) 与 编译标志集合，
            # 模块必须与 core 采用完全一致的口径，否则报
            # "module version/flags mismatch" 拒绝加载（实测）。
            f"OS=linux SCTP=0 "
            f'DEFS_RM="-DHAVE_RESOLV_RES"'
        )

        # 生成 src/config.mak（kamailio 的配置探测；平台按 uname 自动判定）
        self.run(f"make cfg {vars_}", cwd=src)
        # 仅编译目标模块（core 的符号由 kamailio 主程序在运行期提供）
        self.run(f"make modules modules=modules/app_lua {vars_}", cwd=src)

    def package(self):
        src = os.path.join(self.source_folder, "src")
        # 与上游 `make install-modules` 布局一致：$(LIBDIR)/kamailio/app_lua.so
        copy(
            self,
            "app_lua.so",
            src=os.path.join(src, "modules", "app_lua"),
            dst=os.path.join(self.package_folder, "lib", "kamailio"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # 该产物是 kamailio 运行期 dlopen 的插件，不作为链接库使用
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
