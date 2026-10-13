#!/usr/bin/env python3
"""Kamailio xmpp 模块（xmpp.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照同族先例 archives/k/kamailio-http_async/6.0.6、kamailio-xml/6.0.6、
kamailio-db/6.0.6）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 xmpp 模块
    （积分赛任务 kamailio-xmpp 对应 kamailio 源码树内的 modules/xmpp）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule/dlopen 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=xmpp
  make modules modules=modules/xmpp
  模块 Makefile 仅一个外部依赖：expat（DEFS += -I$(LOCALBASE)/include；
  LIBS = -L$(LOCALBASE)/lib -lexpat）——上游 CMakeLists 亦为
  pkg_check_modules(expat REQUIRED)；无 TLS/openssl 依赖。

平台差异（详见同目录 notes.md，均为本版实测）：
1) 平台探测宏：kamailio 以 `uname -s` 判定 OS，OHOS 上是 `HarmonyOS`，不落入
   Makefile.defs 的 linux 分支 → core 头 core/resolve.h:290 直接
   `#error neither gethostbyname2 or getipnodebyname present`。
   对策：显式 `OS=linux`（OHOS 无 harmonyos 专属分支），等价于 linux 分支宏集。
2) 模块 / core 口径一致性（关键）：kamailio 装载模块时在 core/sr_module.c 做两项
   **严格 strcmp**——目标标识 `SER_FULL_VERSION`（= "kamailio 6.0.6 (aarch64/linux)"）
   与 `SER_COMPILE_FLAGS`（ver_defs.h 由 USE_TCP/USE_SCTP/HAVE_RESOLV_RES/分配器/锁等
   展开）。本配方与 OHOS 上 core 口径完全对齐：`SCTP=0`（sysroot 无 netinet/sctp.h）
   + `DEFS_RM=-DHAVE_RESOLV_RES`（OHOS libc 无 _res），否则报
   module version/flags mismatch 拒绝加载。实测已用完整 core 装载本模块通过。
3) expat 探测：模块 Makefile 的 `-I$(LOCALBASE)/include` / `-L$(LOCALBASE)/lib -lexpat`
   经 LOCALBASE 指向 conan expat 包目录（构建机系统 expat 无法介入）；expat 非 OHOS
   sysroot 库（实测 sysroot 无 libexpat*），按 R26 口径由 conan 依赖链提供运行时 .so。
4) -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO
   传令牌，-j>1 有挂起/报错风险；与同族 kamailio-* 配方一致固定 -j1。

补丁（1 个，与平台无关的上游缺陷修复）：xode_from.c 的 _xode_put_expatattribs() 循环条件
   `while(*(atts[i]) != '\0')` 缺少 atts[i] 判空；expat（实测 2.7.3 与 2.8.2 一致）对无属性
   元素传入的是「非 NULL 数组且 atts[0] == NULL」，故该条件直接解引用空指针 → 任何无属性
   元素（<body>/<status>/<show> 等）解析即 SIGSEGV。补 atts[i] != NULL 判空后有属性元素行为
   不变。详见 conandata.yml 与 notes.md（含复现证据与验证方式）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 本包对应上游模块目录名（src/modules/xmpp → xmpp.so）
MODULE = "xmpp"

# OHOS 上 core 的构建口径：OS=linux（无 harmonyos 分支）+ 关闭 SCTP（sysroot 无
# netinet/sctp.h）+ 去掉 HAVE_RESOLV_RES（OHOS libc 无 _res）。
# 二者必须与 core 完全一致，否则 sr_module.c 的 SER_COMPILE_FLAGS strcmp 不通过。
PLATFORM_VARS = 'OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"'


class KamailioXmppConan(ConanFile):
    name = "kamailio-xmpp"
    version = "6.0.6"
    description = ("Kamailio xmpp module: SIP-to-XMPP gateway (component/server), "
                   "XMPP stanza parsing via expat (xode) for HarmonyOS PC")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    # 产物是 kamailio 运行期 dlopen 的共享对象（插件），不声明 shared 选项之外的行为
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # 模块 Makefile 唯一外部依赖：-lexpat。W0 实测制品仓 expat/2.8.2.1.1 可消费
        # （conan download rc=0；包内 libexpat.so 带 SONAME=libexpat.so，消费方
        #  DT_NEEDED 为可重定位的相对名，无绝对路径烤死问题）。
        self.requires("expat/2.8.2.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        expat = self.dependencies["expat"].package_folder
        # R33：编译器从 Conan profile 的 tools.build:compiler_executables 取，
        # 不使用未定义的 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        env = Environment()
        env.define("CC", cc)
        env.define("LD", cc)

        src = os.path.join(self.source_folder, "src")
        # LOCALBASE → conan expat 包目录：模块 Makefile 的 -I/-L/-lexpat 全部解析到依赖包，
        # 构建机系统 expat 无法劫持。BUILDER= 置空：避免版本串掺入构建者信息。
        make_vars = f'LOCALBASE="{expat}" BUILDER= {PLATFORM_VARS}'

        with env.vars(self).apply():
            self.run(f"make cfg include_modules={MODULE} {make_vars}", cwd=src)
            # -j1：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO 传令牌
            self.run(f"make modules modules=modules/{MODULE} -j1 {make_vars}", cwd=src)

        so = os.path.join(src, "modules", MODULE, f"{MODULE}.so")
        if not os.path.isfile(so):
            raise ConanException(f"未产出预期的模块产物: {so}")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", MODULE)
        dst_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        copy(self, f"{MODULE}.so", src=module_dir, dst=dst_dir)
        # 模块文档（消费者配置参考：modparam 与路由函数说明）
        copy(self, "README", src=module_dir,
             dst=os.path.join(self.package_folder, "share", "kamailio", "doc", MODULE))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
