#!/usr/bin/env python3
"""Kamailio IMS 模块集（16 个模块 .so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-extras、kamailio-xml、kamailio-snmpstats 同族先例）：
  - 取官方 kamailio 6.0.6 源码包，仅编译打包 Alpine `kamailio-ims` 子包对应的
    16 个模块（清单见 MODULES，与 Alpine main/kamailio APKBUILD 的
    `_mod_list_ims` 逐项一致）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules="cdp cdp_avp … ims_usrloc_scscf"（共 16 个）
                                         → 生成 src/config.mak
  make modules modules="modules/cdp … modules/ims_usrloc_scscf"（共 16 个）
                                         → 产出 src/modules/<m>/<m>.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏；故经 make 命令行 extra_defs 注入 linux 分支等价宏集
   （宏集与 kamailio-tls/kamailio-xml/kamailio-extras 同族先例一致，均对照 OHOS SDK
   sysroot 实证）。
2) 只编模块不编 core：core/resolve.c（HAVE_RESOLV_RES → `_res`）与 core/lock_ops.h
   （HAVE_UNION_SEMUN → `union semun`）在 OHOS musl 头文件中无对应符号，仅在编译
   kamailio 主程序时才触发；本配方只编 modules，不触碰这两条路径 → **0 补丁**。
3) 三个外部库的探测全部钉死到 conan 依赖包，构建机（含 CI 机器）系统库无从劫持：
   - libxml2（cdp、cdp_avp 之外的 6 个模块：cdp / ims_auth / ims_icscf / ims_isc /
     ims_registrar_pcscf / ims_registrar_scscf）：模块 Makefile 先 `which xml2-config`、
     再 `pkg-config --exists libxml-2.0` 探测，未命中回退 LOCALBASE。配方以命令行变量
     `XML2CFG=`（空值覆盖 Makefile 内部 `$(shell …)` 赋值）钉死 LOCALBASE 回退分支，
     LOCALBASE 指向 conan libxml2 包目录（该包为经典 include/libxml2 布局）。
   - libmnl（ims_ipsec_pcscf）：Makefile 用 `which pkg-config` + `pkg-config --exists
     libmnl` 探测，未命中回退 `-lmnl`。配方以命令行变量 `BUILDER=`（空值）钉死回退
     分支，链接路径由 LIBRARY_PATH 指向 libmnl 包完成。
   - openssl（cdp 的 `ifneq ($(OS),darwin)` 分支无条件追加 `-lssl -lcrypto`）：
     OHOS sysroot/目标机均无 libssl/libcrypto → conan openssl 包提供，
     经 CPATH/LIBRARY_PATH 定位。

链接形态（实测 DT_NEEDED）：libxml2 / libmnl / libssl / libcrypto 在 OHOS sysroot 与
目标机**均不是**系统同名库（sysroot 实证无 libxml2.so/libmnl.so/libssl.so/libcrypto.so），
故按仓库口径（R26）由 conan 依赖链提供运行时 .so；模块 .so 自身不带 RPATH，
部署时经 LD_LIBRARY_PATH 定位，与 kamailio-gcrypt/kamailio-extras 同族先例一致。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Alpine main/kamailio APKBUILD（pkgver=6.0.6）的 _mod_list_ims 逐项一致（16 项）
MODULES = (
    "cdp", "cdp_avp", "ims_auth", "ims_charging", "ims_dialog",
    "ims_diameter_server", "ims_icscf", "ims_ipsec_pcscf", "ims_isc", "ims_ocs",
    "ims_qos", "ims_qos_npn", "ims_registrar_pcscf", "ims_registrar_scscf",
    "ims_usrloc_pcscf", "ims_usrloc_scscf",
)

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

# OHOS sysroot 的 sys/socket.h 与内核 UAPI linux/socket.h **都**定义
# struct sockaddr_storage（前者带 `#ifndef __MUSL__` 守卫）。16 个模块里只有
# ims_ipsec_pcscf 经 libmnl.h 间接引入 linux/netlink.h → linux/socket.h，
# 而 core/ip_addr.h（各模块共用的核心头）使用 sockaddr_storage，两者同 TU 相遇
# 即报 `redefinition of 'sockaddr_storage'`（实测 ipsec.c:38）。
#
# 处置（仅限该模块，其余 15 个模块保持基础宏集不变）：
#   -D__MUSL__                    → 触发 sys/socket.h 的守卫，跳过其同名定义
#   -include linux/socket.h       → 由内核 UAPI 先行提供该结构体（128 字节，
#                                   与 musl 定义布局一致），保证 core/ip_addr.h
#                                   在任何 include 顺序下都拿到完整类型
# 同族先例：archives/a/acpid/2.0.34、archives/a/agetty/2.42.2 的 -D__MUSL__ 用法
# （二者自身即 netlink 程序，全局定义即可；本包其余模块不吃内核头，故按模块收窄）。
MUSL_SCOPED_MODULE = "ims_ipsec_pcscf"
MUSL_SCOPED_DEFS = "-D__MUSL__ -include linux/socket.h"

# IMS 模块集的外部库依赖（OHOS 侧已发布预编译包，制品仓实测存在）
LIBXML2_REF = "libxml2/2.15.3.1"   # 6 个模块（cdp/ims_auth/ims_icscf/ims_isc/ims_registrar_*）
LIBMNL_REF = "libmnl/1.0.5"       # ims_ipsec_pcscf
OPENSSL_REF = "openssl/3.5.8.1"   # cdp（-lssl -lcrypto，非 darwin 分支无条件链接）


class KamailioImsConan(ConanFile):
    name = "kamailio-ims"
    version = "6.0.6"
    description = ("Kamailio IMS modules (16 .so: cdp, cdp_avp, ims_auth, ims_charging, "
                   "ims_dialog, ims_diameter_server, ims_icscf, ims_ipsec_pcscf, ims_isc, "
                   "ims_ocs, ims_qos, ims_qos_npn, ims_registrar_pcscf, "
                   "ims_registrar_scscf, ims_usrloc_pcscf, ims_usrloc_scscf) — "
                   "IP Multimedia Subsystem support")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    # 与同族 11 个 kamailio-* 配方一致的标准形态：本配方现状为 0 补丁
    # （conandata.yml `patches: {}`），两个调用均为 no-op；保留以维持配方族一致性，
    # 并使将来确需补丁时（如上游新版本回归）无需改动结构。
    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def requirements(self):
        self.requires(LIBXML2_REF)
        self.requires(LIBMNL_REF)
        self.requires(OPENSSL_REF)

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

        libxml2 = self.dependencies["libxml2"].package_folder
        libmnl = self.dependencies["libmnl"].package_folder
        openssl = self.dependencies["openssl"].package_folder

        # libxml2 经典布局：头在 include/libxml2 下（libxml2/libxml/*.h）
        dep_includes = os.pathsep.join([
            os.path.join(libxml2, "include", "libxml2"),
            os.path.join(libxml2, "include"),
            os.path.join(libmnl, "include"),
            os.path.join(openssl, "include"),
        ])
        dep_libs = os.pathsep.join([
            os.path.join(libxml2, "lib"),
            os.path.join(libmnl, "lib"),
            os.path.join(openssl, "lib"),
        ])

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CPATH", dep_includes)
        env.define("LIBRARY_PATH", dep_libs)

        defs = " ".join(PLATFORM_DEFS)
        include_modules = " ".join(MODULES)
        # ims_ipsec_pcscf 单独一次 make（需追加 MUSL_SCOPED_DEFS），其余 15 个一批
        plain_modules = [m for m in MODULES if m != MUSL_SCOPED_MODULE]
        module_dirs = " ".join(f"modules/{m}" for m in plain_modules)
        # 依赖探测钉死：命令行变量覆盖模块 Makefile 的探测结果
        #   XML2CFG=（空）→ xml2 系模块走 LOCALBASE 分支（libxml2 包目录）
        #   BUILDER=（空）→ ims_ipsec_pcscf 走 `-lmnl` 分支（路径经 LIBRARY_PATH）
        dep_vars = f"LOCALBASE={libxml2} XML2CFG= BUILDER="

        with env.vars(self).apply():
            self.run(f'make cfg include_modules="{include_modules}" '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)
            # -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver
            # 依赖 FIFO 传令牌，-j>1 存在挂起/报错风险；同族其余 kamailio-* 配方一致用 -j1
            self.run(f'make modules modules="{module_dirs}" -j1 '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)
            # ims_ipsec_pcscf：追加 MUSL_SCOPED_DEFS 消解 sockaddr_storage 重定义
            self.run(f'make modules modules="modules/{MUSL_SCOPED_MODULE}" -j1 '
                     f'extra_defs="{defs} {MUSL_SCOPED_DEFS}" {dep_vars}',
                     cwd=self.source_folder)

        missing = [m for m in MODULES
                   if not os.path.isfile(os.path.join(self.source_folder, "src", "modules",
                                                      m, f"{m}.so"))]
        if missing:
            raise ConanException(f"未产出预期的模块 .so（{len(missing)}/{len(MODULES)}）: {missing}")

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（R51 三步法；完整台账见 notes.md 第四节）。

        清点口径（官方 6.0.6 源码包实测，详见 notes.md §5.1）：
          - 顶层 test/ 目录：0 个；带 test/tests 的目录共 4 个、17 个文件
            （utils/kamctl/dbtextdb/tests 10 + janssonrpcc/test 3 + rtpproxy/test 3 +
            tm/test 1，后三者均非本包模块）
          - **ims 专属上游测试仅 1 处**：src/modules/ims_ipsec_pcscf/spi_list_tests.c
            （配 run_spi_list_tests.sh），但该测试在 6.0.6 已**失效**——它引用
            `spi_node_t.id`，而当前 spi_list.h 的该结构体成员已重构为
            spi_cid/spi_sid/sport/cport，编译即报错（上游测试未随实现同步更新）；
            本配方走 0 补丁路线，不改上游源码，故不执行并如实登记（notes.md §5.3）
          - 16 个模块目录内无 `check`/`ctest` 目标注册（模块 Makefile 无 test 目标）
        因此实跑项为全包唯一自包含、无需运行中 kamailio 实例的上游测试
        utils/kamctl/dbtextdb/dbtextdb_test.py（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库）；ims_ipsec_pcscf 的功能验证由 test_package 以该模块
        真实源码（spi_list.c）驱动的消费者用例承担（notes.md §5.4）。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

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
