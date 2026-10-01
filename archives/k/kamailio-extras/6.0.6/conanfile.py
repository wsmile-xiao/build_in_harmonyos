#!/usr/bin/env python3
"""Kamailio extras 模块集（31 个模块 .so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-tls、kamailio-xml、kamailio-snmpstats 同族先例）：
  - 取官方 kamailio 6.0.6 源码包，仅编译打包 Alpine `kamailio-extras` 子包对应的
    31 个模块（清单见 MODULES，与 Alpine main/kamailio APKBUILD 的
    _mod_list_extras 逐项一致）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules="auth_diameter auth_xkeys call_control … xprint"（共 31 个）
                                         → 生成 src/config.mak
  make modules modules="modules/auth_diameter modules/auth_xkeys …"（共 31 个）
                                         → 产出 src/modules/<m>/<m>.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏；故经 make 命令行 extra_defs 注入 linux 分支等价宏集
   （宏集与 kamailio-tls/kamailio-xml 同族先例一致，均对照 OHOS SDK sysroot 实证）。
2) 只编模块不编 core：core/resolve.c（HAVE_RESOLV_RES → `_res`）与 core/lock_ops.h
   （HAVE_UNION_SEMUN → `union semun`）在 OHOS musl 头文件中无对应符号，仅在编译
   kamailio 主程序时才触发；本配方只编 modules，不触碰这两条路径 → **0 补丁**。
3) cnxcc 依赖探测：cnxcc/Makefile 在 CROSS_COMPILE 为空时用 pkg-config 探测
   hiredis/libevent，未命中回退 LOCALBASE。此处经 make 命令行**直接覆盖**
   HIREDISDEFS/HIREDISLIBS/LEVENTDEFS/LEVENTLIBS（make 命令行变量优先于 Makefile
   内部赋值），钉死到 conan 依赖包目录，构建机系统库无从劫持探测结果。
   链接形态（实测 DT_NEEDED）：hiredis **静态**（OHOS 侧该包仅发布 libhiredis.a，
   API 符号 redisConnect/redisCommand 在 cnxcc.so 中已定义）；libevent **动态**
   （OHOS 侧该包仅发布 .so，且 OHOS sysroot/目标机不含 libevent → 非"系统同名库"，
   按仓库口径由 conan 依赖链提供运行时 .so；cnxcc.so 自身不带 RPATH，
   部署时经 LD_LIBRARY_PATH 定位，与 R26"系统同名库才强制静态"一致）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Alpine main/kamailio APKBUILD（pkgver=6.0.6）的 _mod_list_extras 逐项一致：
# “extra used modules, with no extra dependency”（cnxcc 的 hiredis/libevent 为
# 本配方显式声明的构建期依赖，见 requirements()）。
MODULES = (
    "auth_diameter", "auth_xkeys", "call_control", "call_obj", "cnxcc", "dmq",
    "dmq_usrloc", "domainpolicy", "file_out", "influxdbc", "log_custom", "msrp",
    "nosip", "pdb", "pvtpl", "qos", "rtjson", "sca", "seas", "sms", "ss7ops",
    "sst", "statsd", "tcpops", "timer", "tmrec", "tsilo", "uac_redirect",
    "xhttp", "xhttp_rpc", "xprint",
)

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 与 kamailio-tls/kamailio-xml 同族先例一致（对照 OHOS SDK musl 语义 sysroot 实证存在）。
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

# cnxcc 模块的构建期依赖（OHOS 侧已发布包）
HIREDIS_REF = "hiredis/1.2.0"
LIBEVENT_REF = "libevent/2.1.13"


class KamailioExtrasConan(ConanFile):
    name = "kamailio-extras"
    version = "6.0.6"
    description = ("Kamailio extra modules (31 .so: cnxcc, seas, msrp, dmq, xhttp, "
                   "statsd, influxdbc, rtjson, sca, tsilo, ...)")
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
        self.requires(HIREDIS_REF)
        self.requires(LIBEVENT_REF)

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

        hiredis = self.dependencies["hiredis"].package_folder
        libevent = self.dependencies["libevent"].package_folder

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CPATH", os.pathsep.join([f"{hiredis}/include", f"{libevent}/include"]))
        env.define("LIBRARY_PATH", os.pathsep.join([f"{hiredis}/lib", f"{libevent}/lib"]))

        defs = " ".join(PLATFORM_DEFS)
        include_modules = " ".join(MODULES)
        module_dirs = " ".join(f"modules/{m}" for m in MODULES)
        # cnxcc：命令行变量覆盖模块 Makefile 的探测结果，钉死 conan 依赖包
        # （hiredis 包内仅 .a → 静态链入；libevent 包内仅 .so → 动态依赖）
        dep_vars = (
            f'HIREDISDEFS=-I{hiredis}/include HIREDISLIBS="-L{hiredis}/lib -lhiredis" '
            f'LEVENTDEFS=-I{libevent}/include LEVENTLIBS="-L{libevent}/lib -levent"'
        )

        with env.vars(self).apply():
            self.run(f'make cfg include_modules="{include_modules}" extra_defs="{defs}"',
                     cwd=self.source_folder)
            # -j1（E525/E074）：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver
            # 依赖 FIFO 传令牌，-j>1 存在挂起/报错风险；同族其余 10 个 kamailio-* 配方一致用 -j1
            self.run(f'make modules modules="{module_dirs}" -j1 '
                     f'extra_defs="{defs}" {dep_vars}',
                     cwd=self.source_folder)

        missing = [m for m in MODULES
                   if not os.path.isfile(os.path.join(self.source_folder, "src", "modules",
                                                      m, f"{m}.so"))]
        if missing:
            raise ConanException(f"未产出预期的模块 .so（{len(missing)}/{len(MODULES)}）: {missing}")

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
