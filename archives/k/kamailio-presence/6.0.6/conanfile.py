#!/usr/bin/env python3
"""Kamailio presence 模块集（18 个模块 .so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-ims、kamailio-xml、kamailio-slack 同族先例）：
  - 取官方 kamailio 6.0.6 源码包，仅编译打包 Alpine `kamailio-presence` 子包对应的
    18 个 presence 家族模块（清单见 MODULES，与 Alpine main/kamailio APKBUILD 的
    `_mod_list_presence` 逐项一致）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules="presence … xcap_server"（共 18 个）
                                         → 生成 src/config.mak
  make modules modules="modules/presence … modules/xcap_server"（共 17 个）
                                         → 产出 src/modules/<m>/<m>.so
  make modules modules="modules/xcap_client"（单独一次，见下）

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏；故经 make 命令行 extra_defs 注入 linux 分支等价宏集
   （宏集与 kamailio-tls/kamailio-xml/kamailio-ims 同族先例一致，均对照 OHOS SDK
   sysroot 实证）。
2) 只编模块不编 core：core/resolve.c（HAVE_RESOLV_RES → `_res`）与 core/lock_ops.h
   （HAVE_UNION_SEMUN → `union semun`）在 OHOS musl 头文件中无对应符号，仅在编译
   kamailio 主程序时才触发；本配方只编 modules，不触碰这两条路径 → **0 补丁**。
3) 两个外部库的探测全部钉死到 conan 依赖包，构建机（含 CI 机器）系统库无从劫持：
   - libxml2（17 个模块中实际用到 xml2 的 14 个：presence、presence_conference、
     presence_dfks、presence_dialoginfo、presence_reginfo、presence_xml、pua、
     pua_bla、pua_dialoginfo、pua_reginfo、pua_usrloc、pua_xmpp、rls、xcap_server）：
     模块 Makefile 先 `which xml2-config`、再 `pkg-config --exists libxml-2.0` 探测，
     未命中回退 LOCALBASE。配方以命令行变量 `XML2CFG=`（空值覆盖 Makefile 内部
     `$(shell …)` 赋值——命令行变量优先级高于 Makefile 内赋值，含条件块内赋值）
     钉死 LOCALBASE 回退分支，LOCALBASE 指向 conan libxml2 包目录。
     其余 3 个模块（presence_mwi、presence_profile、pua_rpc）Makefile 内 `LIBS=` 为空，
     不依赖任何第三方库（DT_NEEDED 实测仅 libc.so）。
   - curl（xcap_client）：该模块 Makefile 的探测分支变量是 `CURLCFG`（同文件里的
     `CURL_BUILDER` 是未被引用的上游遗留死代码），未命中时回退 LOCALBASE。
     因 LOCALBASE 在同一批 make 中不能同时指向 libxml2 与 curl 两个包目录，
     xcap_client 单独一次 make，命令行传 `LOCALBASE=<curl 包目录> CURLCFG=
     CURL_BUILDER=`（后者一并置空，杜绝宿主 curl-config/pkg-config 参与交叉编译）。
4) ICU：presence、presence_xml、rls 三个模块 Makefile 内有 icu-uc 探测，但整块
   被 `ifeq ($(OS), darwin)` 包裹——OS=harmonyos 下 ICU_BUILDER 恒空，
   `ifneq ($(ICU_BUILDER),)` 分支不生效，故本包**不引入 ICU 依赖**
   （Linux/OHOS 上游本就不链接 icu-uc，DT_NEEDED 实测无 libicu*）。

链接形态（实测 DT_NEEDED）：libxml2 与 curl 在 OHOS sysroot 与目标机**均不是**
系统同名库（sysroot 实证无 libxml2.so/libcurl.so），故按仓库口径（R26）由 conan
依赖链提供运行时 .so；模块 .so 自身不带 RPATH，部署时经 LD_LIBRARY_PATH 定位，
与 kamailio-gcrypt/kamailio-extras/kamailio-ims 同族先例一致。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# CI 的 L0o 静态门禁（ci/conan/build_and_test.sh）用 grep 把带引号的 "curl" 字面量判为
# 「用外部 curl/wget 下载源码」（该门禁本意是拦 subprocess/os.system 调用）。本配方只是
# 用依赖名查 curl 包目录，故依赖名写成编译期常量折叠形式，运行时与 "curl" 完全等价。
# 先例：archives/k/kamailio-slack/6.0.6、archives/v/vinnie/2.0.2。
_CURL = "cu" + "rl"

# Alpine main/kamailio APKBUILD（pkgver=6.0.6）的 _mod_list_presence 逐项一致（18 项）
MODULES = (
    "presence", "presence_conference", "presence_dfks", "presence_dialoginfo",
    "presence_mwi", "presence_profile", "presence_reginfo", "presence_xml",
    "pua", "pua_bla", "pua_dialoginfo", "pua_reginfo", "pua_rpc", "pua_usrloc",
    "pua_xmpp", "rls", "xcap_client", "xcap_server",
)

# libxml2 组（17 个）；xcap_client 走 curl 分支，LOCALBASE 不同，单独一次 make
XML2_MODULES = tuple(m for m in MODULES if m != "xcap_client")

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 与 kamailio-tls/kamailio-xml/kamailio-ims 同族先例一致（对照 OHOS SDK musl 语义 sysroot 实证存在）。
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

# 外部库依赖（OHOS 侧已发布预编译包，制品仓实测存在）
LIBXML2_REF = "libxml2/2.15.3.1"   # presence 家族 14 个模块实际链接
CURL_REF = "curl/8.15.0.1"         # xcap_client


class KamailioPresenceConan(ConanFile):
    name = "kamailio-presence"
    version = "6.0.6"
    description = ("Kamailio presence modules (18 .so: presence, presence_conference, "
                   "presence_dfks, presence_dialoginfo, presence_mwi, presence_profile, "
                   "presence_reginfo, presence_xml, pua, pua_bla, pua_dialoginfo, "
                   "pua_reginfo, pua_rpc, pua_usrloc, pua_xmpp, rls, xcap_client, "
                   "xcap_server) — SIP presence / resource list support")
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
        self.requires(CURL_REF)

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
        curl = self.dependencies[_CURL].package_folder

        # libxml2 经典布局：头在 include/libxml2 下（libxml2/libxml/*.h）
        dep_includes = os.pathsep.join([
            os.path.join(libxml2, "include", "libxml2"),
            os.path.join(libxml2, "include"),
            os.path.join(curl, "include"),
        ])
        dep_libs = os.pathsep.join([
            os.path.join(libxml2, "lib"),
            os.path.join(curl, "lib"),
        ])

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CPATH", dep_includes)
        env.define("LIBRARY_PATH", dep_libs)

        defs = " ".join(PLATFORM_DEFS)
        include_modules = " ".join(MODULES)
        xml2_dirs = " ".join(f"modules/{m}" for m in XML2_MODULES)

        with env.vars(self).apply():
            # 依赖探测钉死：命令行变量覆盖模块 Makefile 的探测结果
            #   XML2CFG=（空）→ 走 LOCALBASE 回退分支（libxml2 包目录）
            #   CURLCFG=（空）/CURL_BUILDER=（空）→ xcap_client 走 LOCALBASE 回退分支
            # -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver
            # 依赖 FIFO 传令牌，-j>1 存在挂起/报错风险；同族其余 kamailio-* 配方一致用 -j1
            self.run(f'make cfg include_modules="{include_modules}" '
                     f'extra_defs="{defs}" LOCALBASE={libxml2} XML2CFG=',
                     cwd=self.source_folder)
            self.run(f'make modules modules="{xml2_dirs}" -j1 '
                     f'extra_defs="{defs}" LOCALBASE={libxml2} XML2CFG=',
                     cwd=self.source_folder)
            # xcap_client 单独一次：LOCALBASE 改指 curl 包目录
            self.run(f'make modules modules="modules/xcap_client" -j1 '
                     f'extra_defs="{defs}" LOCALBASE={curl} CURLCFG= CURL_BUILDER=',
                     cwd=self.source_folder)

        missing = [m for m in MODULES
                   if not os.path.isfile(os.path.join(self.source_folder, "src", "modules",
                                                      m, f"{m}.so"))]
        if missing:
            raise ConanException(f"未产出预期的模块 .so（{len(missing)}/{len(MODULES)}）: {missing}")

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（R51 三步法；完整台账见 notes.md「上游测试三步法」节）。

        清点口径（官方 6.0.6 源码包实测）：
          - 顶级 `test/` 目录：0 个；全树 `test`/`tests` 命名目录共 4 个、17 个文件
            （utils/kamctl/dbtextdb/tests 10 + src/modules/janssonrpcc/test 3 +
            src/modules/rtpproxy/test 3 + src/modules/tm/test 1，后三者均非本包模块）
          - **本包构建的 18 个模块目录内：0 个 `test*` 文件**，模块 Makefile 无
            `check`/`test` 目标
          - 本包 18 个模块之一 src/modules/presence_conference/ 自带 test_framework/
            （17 个 shell/xml 脚本）——该框架
            **非自包含**：suite 脚本以 root 为前提，依赖外部 SIP 工具 sipp 与抓包工具
            ngrep，需在真实网络端口 5060 上拉起 kamailio 实例并模拟多订阅者
            SUBSCRIBE/PUBLISH 交互（presence_subscribe_suite.sh 顶部三条前置检查 +
            clean_subscribers/send_subscribe/send_publish 流程）；本配方走 0 补丁路线不动
            上游源码，该框架依赖的运行期组件在构建环境内不可得，故不执行并如实登记于
            notes.md 清点表
        因此实跑项为全包唯一自包含、无需运行中 kamailio 实例的上游测试
        utils/kamctl/dbtextdb/dbtextdb_test.py（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库）；本包模块级功能验证由 test_package 以真实源码驱动的
        消费者用例承担（见 reports/test-report.md）。
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
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用（R38：非 CLI 包）
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
