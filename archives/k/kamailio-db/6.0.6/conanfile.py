#!/usr/bin/env python3
"""Conan recipe: kamailio-db 6.0.6 (kamailio DB-backend 模块集, 33 个 .so) for HarmonyOS PC.

目标库 `kamailio-db` 是发行版二进制子包名（Alpine `kamailio` 的 `db` 子包，描述
"Kamailio modules using a database backend"），对应上游工程 Kamailio SIP Server
6.0.6 中 `_mod_list_db` 所列 **33 个模块**（产物 33 个 `*.so`）。

打包口径（与 Alpine main/kamailio APKBUILD 的 `_mod_list_db`(pkgver=6.0.6) 逐项一致）:
  acc alias_db auth_db avpops cfg_db db_cluster db_flatstore dialog dispatcher
  domain drouting group htable imc matrix mohqueue msilo mtree pdt permissions
  pipelimit prefix_route p_usrloc registrar sipcapture siptrace speeddial sqlops
  topos_htable uac uri_db userblocklist usrloc

  * 这是"使用数据库后端 API"的模块集，**不含**具体 DB 驱动（db_mysql / db_postgres /
    db_unixodbc / db_sqlite / db_text / db_berkeley 分属独立子包）。
  * 不依赖 kamailio 本体包：模块 .so 由 kamailio 运行时 loadmodule(dlopen) 加载，
    core 符号由主程序在 RTLD_GLOBAL 下提供。

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（`src/Makefile` + `Makefile.defs`）
  make cfg OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"           → 生成 src/config.mak
  make modules modules="modules/acc modules/alias_db … modules/usrloc" -j1 同上口径
                                                                 → 产出 33 个 <m>.so

平台差异（详见同目录 notes.md，均为本版实测）：
1) 平台探测宏：kamailio 以 `uname -s` 判定 OS，OHOS 上是 `HarmonyOS`，不落入
   Makefile.defs 的 linux 分支 → core 头 `core/resolve.h:290` 直接 `#error
   neither gethostbyname2 or getipnodebyname present`（首个真实错误）。
   对策：显式 `OS=linux`（OHOS 无 harmonyos 专属分支），等价于 linux 分支宏集。
2) 模块 / core 口径一致性（关键）：kamailio 加载模块时做两项校验——目标标识
   `(aarch64/<os>)` 与编译标志集合。本配方与 OHOS 上 core 口径完全对齐：
   `SCTP=0`（sysroot 无 netinet/sctp.h）+ `DEFS_RM=-DHAVE_RESOLV_RES`（OHOS libc 无
   `_res`），否则报 module version/flags mismatch 拒绝加载。
3) 0 补丁：33 个成员模块源码不含平台条件编译（实测 `__OS_*` 仅 solaris/darwin 分支，
   无 `__OHOS__`/`HAVE_*` 命中）；仅 dispatcher 的 Makefile 带 `LIBS=-lm`（系统库，
   OHOS musl 下并入 libc，实际无独立 DT_NEEDED）。
4) -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO
   传令牌，-j>1 有挂起/报错风险；与同族 kamailio-* 配方一致固定 -j1。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Alpine main/kamailio APKBUILD（pkgver=6.0.6）的 _mod_list_db 逐项一致（33 个）。
# 注：Alpine 注释明确 "Remove db_text from _mod_list_db because we create a separate
# dbtext package"；src/Makefile.groups 的 mod_list_db 另含 db_text 与 secfilter，此处
# 以 Alpine 子包口径为准（子包名 kamailio-db 的权威成员表）。
MODULES = (
    "acc", "alias_db", "auth_db", "avpops", "cfg_db", "db_cluster", "db_flatstore",
    "dialog", "dispatcher", "domain", "drouting", "group", "htable", "imc", "matrix",
    "mohqueue", "msilo", "mtree", "pdt", "permissions", "pipelimit", "prefix_route",
    "p_usrloc", "registrar", "sipcapture", "siptrace", "speeddial", "sqlops",
    "topos_htable", "uac", "uri_db", "userblocklist", "usrloc",
)

# OHOS 上 core 的构建口径：OS=linux（无 harmonyos 分支）+ 关闭 SCTP（sysroot 无
# netinet/sctp.h）+ 去掉 HAVE_RESOLV_RES（OHOS libc 无 _res）。
PLATFORM_VARS = 'OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"'


class KamailioDbConan(ConanFile):
    name = "kamailio-db"
    version = "6.0.6"
    description = ("Kamailio (SIP server) database-backend module set - 33 modules "
                   "(acc, auth_db, avpops, dialog, dispatcher, htable, permissions, "
                   "registrar, siptrace, sqlops, usrloc, ...) for HarmonyOS PC")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 产物是 kamailio 运行期 dlopen 的共享对象（插件），不声明 shared 选项
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    # 与同族 kamailio-* 配方一致的标准形态：本配方现状为 0 补丁（conandata.yml
    # `patches: {}`），两处调用均为 no-op；保留以维持配方族一致性，并使将来确需补丁时
    # 无需改动结构。
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器从 Conan profile 的 tools.build:compiler_executables 取，
        # 不使用未定义的 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)

        src = os.path.join(self.source_folder, "src")
        module_dirs = " ".join(f"modules/{m}" for m in MODULES)
        ccvars = f'CC="{cc}" LD="{cc}"'

        with env.vars(self).apply():
            self.run(f"make cfg {PLATFORM_VARS} {ccvars}", cwd=src)
            # -j1：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO 传令牌
            self.run(f'make modules modules="{module_dirs}" -j1 {PLATFORM_VARS} {ccvars}', cwd=src)

        missing = [m for m in MODULES
                   if not os.path.isfile(os.path.join(src, "modules", m, f"{m}.so"))]
        if missing:
            raise ConanException(
                f"未产出预期的模块 .so（{len(missing)}/{len(MODULES)}）: {missing}")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        dst_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        for module in MODULES:
            copy(self, f"{module}.so",
                 src=os.path.join(self.source_folder, "src", "modules", module),
                 dst=dst_dir)

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
