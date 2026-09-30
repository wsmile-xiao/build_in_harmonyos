#!/usr/bin/env python3
"""Kamailio gcrypt 模块（gcrypt.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-tls、kamailio-xml、kamailio-unixodbc 同族先例）：
  - 取官方 kamailio 6.0.6 源码包，仅编译打包 Alpine `kamailio-gcrypt` 子包对应的
    单个模块 gcrypt.so（与 Alpine main/kamailio APKBUILD 的
    `_mod_list_gcrypt="gcrypt"` 逐项一致）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules="gcrypt"        → 生成 src/config.mak
  make modules modules="modules/gcrypt"    → 产出 src/modules/gcrypt/gcrypt.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏；故经 make 命令行 extra_defs 注入 linux 分支等价宏集
   （宏集与 kamailio-tls/kamailio-xml/kamailio-extras 同族先例一致，均对照 OHOS SDK
   sysroot 实证）。
2) 只编模块不编 core：core/resolve.c（HAVE_RESOLV_RES → `_res`）与 core/lock_ops.h
   （HAVE_UNION_SEMUN → `union semun`）在 OHOS musl 头文件中无对应符号，仅在编译
   kamailio 主程序时才触发；本配方只编 modules，不触碰这两条路径 → **0 补丁**。
3) libgcrypt 依赖探测：gcrypt/Makefile 在 CROSS_COMPILE 为空时用
   `pkg-config --exists libgcrypt` 探测（命中则取 --cflags/--libs），未命中回退
   LOCALBASE。此处三重钉死，构建机系统库无从劫持探测结果：
     - 命令行变量 GCRYPT_BUILDER="pkg-config libgcrypt"（make 命令行变量优先于
       Makefile 内部赋值），配合 PKG_CONFIG_PATH 指向 conan 依赖包 → 命中即取
       依赖包内 .pc 的 flags；
     - CPATH/LIBRARY_PATH 指向 conan 依赖包（pkg-config 缺失时仍可编译/链接）；
     - LOCALBASE 指向 libgcrypt 包目录（回退分支亦指向依赖包）。

链接形态：libgcrypt 在 OHOS sysroot/目标机**不是**系统同名库（无 libgcrypt.so），
故按仓库口径（R26）由 conan 依赖链提供运行时 .so，gcrypt.so 自身不带 RPATH，
部署时经 LD_LIBRARY_PATH 定位；实测依赖形态见同目录 notes.md。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Alpine main/kamailio APKBUILD（pkgver=6.0.6）的 _mod_list_gcrypt 逐项一致
MODULES = ("gcrypt",)

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 与 kamailio-tls/kamailio-xml/kamailio-extras 同族先例一致（对照 OHOS SDK musl 语义 sysroot 实证存在）。
PLATFORM_DEFS = (
    "-D_GNU_SOURCE",
    "-DHAVE_GETHOSTBYNAME2",
    "-DHAVE_SCHED_YIELD",
    "-DHAVE_MSG_NOSIGNAL",
    "-DHAVE_MSGHDR_MSG_CONTROL",
    "-DHAVE_ALLOCA_H",
    "-DHAVE_TIMEGM",
    "-DHAVE_SCHED_SETSCHEDULER",
    "-DHAVE_IP_MREQN",
)

# gcrypt 模块的构建期依赖（OHOS 侧已发布包）
LIBGCRYPT_REF = "libgcrypt/1.12.2"


class KamailioGcryptConan(ConanFile):
    name = "kamailio-gcrypt"
    version = "6.0.6"
    description = "Kamailio gcrypt module: cryptography functions using libgcrypt (gcrypt.so)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    # 与同族 10 个 kamailio-* 配方一致的标准形态：本配方现状为 0 补丁
    # （conandata.yml `patches: {}`），两个调用均为 no-op；保留以维持配方族一致性，
    # 并使将来确需补丁时（如上游新版本回归）无需改动结构。
    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(LIBGCRYPT_REF)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 0 补丁现状下为 no-op（conandata.yml `patches: {}`）；与同族配方保持同构。
        apply_conandata_patches(self)

        # R33：编译器与依赖路径全部显式注入，不使用未定义的 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"

        libgcrypt = self.dependencies["libgcrypt"].package_folder
        libgpg_error = self.dependencies["libgpg-error"].package_folder
        dep_includes = os.pathsep.join(
            [os.path.join(libgcrypt, "include"), os.path.join(libgpg_error, "include")])
        dep_libs = os.pathsep.join(
            [os.path.join(libgcrypt, "lib"), os.path.join(libgpg_error, "lib")])
        dep_pc = os.pathsep.join(
            [os.path.join(libgcrypt, "lib", "pkgconfig"),
             os.path.join(libgpg_error, "lib", "pkgconfig")])

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CPATH", dep_includes)
        env.define("LIBRARY_PATH", dep_libs)
        env.define("PKG_CONFIG_PATH", dep_pc)

        defs = " ".join(PLATFORM_DEFS)
        # gcrypt 模块依赖探测：命令行变量覆盖模块 Makefile 的探测结果，钉死 conan 依赖包
        # （make 命令行变量优先于 Makefile 内部赋值：GCRYPT_BUILDER / LOCALBASE）
        dep_vars = f'GCRYPT_BUILDER="pkg-config libgcrypt" LOCALBASE={libgcrypt}'

        with env.vars(self).apply():
            self.run(f'make cfg include_modules="{" ".join(MODULES)}" '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)
            # -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver
            # 依赖 FIFO 传令牌，-j>1 存在挂起/报错风险；同族其余 kamailio-* 配方一致用 -j1
            self.run(f'make modules modules="{" ".join("modules/" + m for m in MODULES)}" -j1 '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)

        missing = [m for m in MODULES
                   if not os.path.isfile(os.path.join(self.source_folder, "src", "modules",
                                                      m, f"{m}.so"))]
        if missing:
            raise ConanException(f"未产出预期的模块 .so（{len(missing)}/{len(MODULES)}）: {missing}")

        # R51 上游测试三步法之「可运行环境实际运行」层证据：
        # gcrypt 模块自身无上游测试（源码包 test/tests 全量 17 个文件 / 4 个目录，无一
        # 涉及 gcrypt，清点台账见 test_package/MANIFEST.yml）。源码包内唯一自包含、
        # 无需运行中 kamailio 实例的上游测试是 utils/kamctl/dbtextdb/dbtextdb_test.py
        # （上游自带 unittest 入口，3 个用例，仅依赖 Python 标准库）——此处真实执行。
        dbtextdb = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        if os.path.isfile(os.path.join(dbtextdb, "dbtextdb_test.py")):
            self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=dbtextdb)

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
