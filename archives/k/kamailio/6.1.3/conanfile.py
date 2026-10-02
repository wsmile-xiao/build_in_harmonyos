#!/usr/bin/env python3
"""Kamailio core（主二进制 kamailio）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-tls/6.0.6 同族先例）：
  - 取官方 kamailio 6.1.3 源码包构建 core（主二进制），不含任何附加模块
  - 无外部 conan 依赖：pcre2 仅被 modules 引用，core 不引用（源码级清点）
  - 无独立 libkamailio.so/.a：core 目标代码直接链入主二进制；二进制按
    ET_DYN（PIE）构建，运行时 dlopen 加载模块
  - srved 在 6.1.3 源码树中不存在（上游早已移除），无此交付物

构建体系：kamailio 6.1.3 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg  extra_defs='…'                       → 生成 src/config.mak
  env DEFS=-UHAVE_RESOLV_RES make -j4 extra_defs='…' → 产出 src/kamailio

三处平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 等分支，
   OS=harmonyos 不注入任何 HAVE_* 探测宏。经 `extra_defs` 注入 linux 分支
   等价宏集（9 平台宏，6.0.6 模块族已实证，E429）。
2) core 相对模块的两处新增（core 首次触达）：
   a. 锁机制：无平台分支时 found_lock_method 未置位，core lock_ops.h #error
      "no locking method selected" → 注入 -DUSE_PTHREAD_MUTEX（linux 分支默认值）。
   b. _res 全局：-DHAVE_RESOLV_RES 在 Makefile.defs 无条件定义，musl resolv.h
      不导出 _res 全局 → core/resolve.c 编译失败。修复 = env DEFS=-UHAVE_RESOLV_RES
      （$(DEFS) 在编译行位于 $(C_DEFS) 之后，后置 -U 胜出；必须用环境变量而非
      make 命令行——命令行变量会锁定并吞掉 main.o 的目标特定 DEFS+=-DMODS_DIR；
      extra_defs 位于 -D 之前亦不可行）。守卫变假后走上游自带 #else 回退分支，
      零源码改动、零补丁。
3) HAVE_EPOLL 注入（已实证）：不注入则事件循环回退 poll（`kamailio -v` 仅
   "poll method support: poll."）；注入后与 linux 构建对齐
   （"poll, epoll_lt, epoll_et."）。HAVE_SIGIO_RT/USE_FUTEX 不注入：
   最小参数原则，回退路径完备（notes.md §2 对照表）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 前 9 个符号均已对照 OHOS SDK（musl 语义）sysroot 头文件实证（6.0.6 模块族
# 同口径，E429）；后 2 个为 core 构建所需：
#   USE_PTHREAD_MUTEX：linux 分支默认锁机制（lock_ops.h 无定义时 #error）；
#   HAVE_EPOLL：linux 分支条件宏（≥2.5.44），注入后事件循环对齐 linux 构建，
#   已在 OHOS/musl 实证编译与 -v 输出。
CORE_DEFS = (
    "-D_GNU_SOURCE",
    "-DHAVE_GETHOSTBYNAME2",
    "-DHAVE_SCHED_YIELD",
    "-DHAVE_MSG_NOSIGNAL",
    "-DHAVE_MSGHDR_MSG_CONTROL",
    "-DHAVE_ALLOCA_H",
    "-DHAVE_TIMEGM",
    "-DHAVE_SCHED_SETSCHEDULER",
    "-DHAVE_IP_MREQN",
    "-DUSE_PTHREAD_MUTEX",
    "-DHAVE_EPOLL",
)


class KamailioConan(ConanFile):
    name = "kamailio"
    version = "6.1.3"
    description = ("Kamailio core: high-performance open-source SIP server "
                   "(main binary; modules load at runtime via loadmodule)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"
    topics = ("sip", "voip", "proxy")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"

        # R33：编译器显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        # musl 不导出 _res 全局：后置 -U 撤销无条件定义的 -DHAVE_RESOLV_RES
        #（必须环境变量，见模块 docstring 差异 2b）
        env.define("DEFS", "-UHAVE_RESOLV_RES")

        extra = " ".join(CORE_DEFS)
        with env.vars(self).apply():
            self.run(f"make cfg extra_defs='{extra}'", cwd=self.source_folder)
            self.run(f"make -j4 extra_defs='{extra}'", cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "kamailio", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
