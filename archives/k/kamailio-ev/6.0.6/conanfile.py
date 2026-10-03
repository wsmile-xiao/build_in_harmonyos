#!/usr/bin/env python3
"""Kamailio evapi 模块（evapi.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-{tls,gcrypt,xml,unixodbc,extras} 同族先例）：
  - 取官方 kamailio 6.0.6 源码包，仅编译打包 Alpine `kamailio-ev` 子包对应的
    单个模块 evapi.so（与 Alpine main/kamailio APKBUILD 的 `_mod_list_ev="evapi"` 一致）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules="evapi"          → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules="modules/evapi"      → 产出 src/modules/evapi/evapi.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏；故经 make 命令行 extra_defs 注入 linux 分支等价宏集
   （宏集与同族 kamailio-tls/gcrypt/xml/extras 先例一致，均对照 OHOS SDK sysroot 实证）。
2) libev 依赖探测（本模块特有）：evapi/Makefile 在 CROSS_COMPILE 为空时先
   `pkg-config --exists libev` 探测，命中则取 `--cflags/--libs libev`；未命中回退
   `-I$(LOCALBASE)/include` + `-L$(LOCALBASE)/lib -lev`。注意变量名是**裸 BUILDER**，
   与 tls（SSL_BUILDER）/gcrypt（GCRYPT_BUILDER）不同。
   conan 制品仓的 libev/4.33 **不携带 .pc 文件**，且构建机若装有系统 libev（带 .pc）
   会劫持探测结果指向构建机路径（交叉编译事故源）。故显式传 `BUILDER=`（make 命令行
   变量优先于 Makefile 内部赋值）钉死 LOCALBASE 回退分支，LOCALBASE 指向 conan libev
   包目录；CPATH/LIBRARY_PATH 同样指向依赖包，形成双重保险。
   实测（logs/builder-pin-experiment.log）：假 pkg-config 置于 PATH 时，不传 BUILDER=
   会被劫持为 `-L/FAKE_HIJACK/lib -lev`；传 BUILDER= 后稳定走 LOCALBASE 回退。

链接形态：libev 在 OHOS sysroot/目标机**不是**系统同名库（无 libev.so），故按仓库
口径（R26）由 conan 依赖链提供运行时 .so，evapi.so 自身不带 RPATH，部署时经
LD_LIBRARY_PATH 定位；实测依赖形态见同目录 notes.md。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Alpine main/kamailio APKBUILD（pkgver=6.0.6）的 _mod_list_ev 逐项一致
MODULES = ("evapi",)

# libev 为 evapi 模块唯一强制第三方依赖（evapi/CMakeLists.txt find_package(Libev REQUIRED)、
# evapi/Makefile -lev、APKBUILD makedepends libev-dev、模块 README:139）
LIBEV_REF = "libev/4.33"

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 与 kamailio-tls/kamailio-gcrypt/kamailio-xml/kamailio-extras 同族先例一致（对照 OHOS SDK musl 语义 sysroot 实证存在）。
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


class KamailioEvConan(ConanFile):
    name = "kamailio-ev"
    version = "6.0.6"
    description = ("Kamailio evapi module: network event broadcast API (libev-based event "
                   "socket interface, evapi.so)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    # 与同族 kamailio-* 配方一致的标准形态：本配方 0 补丁（conandata.yml `patches: {}`），
    # 两个调用均为 no-op；保留以维持配方族一致性。
    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(LIBEV_REF)

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

        libev = self.dependencies["libev"].package_folder

        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", os.path.join(libev, "include"))
        env.define("LIBRARY_PATH", os.path.join(libev, "lib"))

        defs = " ".join(PLATFORM_DEFS)
        # evapi 模块依赖探测钉死：BUILDER= 置空即跳过模块 Makefile 的 pkg-config 分支，
        # 强制走 LOCALBASE 回退（libev 包无 .pc，且构建机同名系统库不得劫持探测结果）。
        dep_vars = f'BUILDER= LOCALBASE="{libev}"'

        with env.vars(self).apply():
            self.run(f'make cfg include_modules="{" ".join(MODULES)}" '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)
            # -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver
            # 依赖 FIFO 传递令牌，-j>1 存在挂起/报错风险；同族其余 kamailio-* 配方一致用 -j1
            self.run(f'make modules modules="{" ".join("modules/" + m for m in MODULES)}" -j1 '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)

        missing = [m for m in MODULES
                   if not os.path.isfile(os.path.join(self.source_folder, "src", "modules",
                                                      m, f"{m}.so"))]
        if missing:
            raise ConanException(f"未产出预期的模块 .so（{len(missing)}/{len(MODULES)}）: {missing}")

        # R51 上游测试三步法之「可运行环境实际运行」层证据：
        # evapi 模块自身无上游测试（源码包 test/tests 全量 17 个文件 / 4 个目录，无一涉及
        # evapi，清点台账见 test_package/MANIFEST.yml）。源码包内唯一自包含、无需运行中
        # kamailio 实例的上游测试是 utils/kamctl/dbtextdb/dbtextdb_test.py（上游自带
        # unittest 入口，3 个用例，仅依赖 Python 标准库）——此处真实执行。
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
