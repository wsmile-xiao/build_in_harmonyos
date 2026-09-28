#!/usr/bin/env python3
"""Conan recipe for sash 3.8 — stand-alone shell for system recovery.

sash 是 David I. Bell 写的救援用独立 shell：把大量标准工具（-gzip/-tar/
-ar/-ls/-find/-grep/-dd/-ed ...）内建进同一个可执行文件，用于"共享库或
可执行文件缺失时还能救系统"。构建系统是裸 GNU Makefile（无 configure、
无 CMake、无 meson），唯一外部依赖是 zlib（Makefile: LIBS = -lz，服务
-gzip / -gunzip 两条内建命令）。

OHOS 适配点（完整推导与证据见同目录 notes.md）：

1. HAVE_LINUX_ATTR=0 —— 上游开关，不改源码。
   cmd_chattr.c 整个文件体由 `#if HAVE_LINUX_ATTR`(L11)…`#endif`(L262)
   包住，其中 #include <ext2fs/ext2_fs.h>；OHOS native SDK sysroot 无该
   头（已实测 MISSING）。关掉即从命令表里移除 -chattr/-lsattr 两条内建
   （sash.c 中登记处同样被 #if HAVE_LINUX_ATTR 包住），属合法的上游功能
   面收缩，优于引第二个 source、优于引入 e2fsprogs。

2. LDFLAGS 覆盖掉上游的 `-static`。
   上游 `-static` 是"整程序静态链"，与 conan 依赖链管理相冲（zlib 是
   conan 依赖）。注意这**不牺牲上游救援语义**：制品仓 zlib/1.3.1 的 OHOS
   包只提供 libz.a（R26 系统同名库强制静态，已实测包目录内只有 libz.a、
   无 libz.so），所以 `-lz` 仍是静态吃入，sash 不因此新增任何运行时 .so
   依赖；只有 libc/libm 等基础运行时回到动态。

3. 上游 CFLAGS 一字不改地保住。
   Makefile 用 `CFLAGS = ...`（含全部 -DHAVE_* 与 -Wall/-Wmissing-
   prototypes），所以**不覆盖 CFLAGS**，只经 make 命令行注入 CPPFLAGS
   （zlib 头路径）与 LDFLAGS（zlib 库路径，且不带 -static）；命令行变量
   优先级高于 makefile 内赋值（Makefile 无 override 指令），而隐式规则
   `$(CC) $(CFLAGS) $(CPPFLAGS) -c` 会让 CPPFLAGS 一并落到编译行上。

4. MOUNT_TYPE 传参修正（上游 Makefile 的引号层次在 sh 下不成立）。
   Makefile 有 `type = MOUNT_TYPE;`（cmds.c:670，const char *），而
   `MOUNT_TYPE = '"ext3"'` 展开成编译行的 `-DMOUNT_TYPE="ext3"` 后，双
   引号会被 shell 引号剥离吃掉 → clang 收到 `-DMOUNT_TYPE=ext3` → 报
   `use of undeclared identifier 'ext3'`（本机已三态实测，见 notes.md）。
   改为传 `MOUNT_TYPE='\"ext3\"'`：字面反斜杠先躲过 shell，进 clang 时
   还原为 `-DMOUNT_TYPE="ext3"`，宏值仍是字符串 "ext3"，**与上游默认值
   语义完全一致**。

5. 不走 `make install`。
   上游 install 规则把 BINDIR 写死 /bin、MANDIR 写死 /usr/man（不是
   /usr/share/man）且用裸 `cp`；改在 package() 里按 conan 布局直接落
   bin/sash 与 share/man/man1/sash.1，免掉前缀覆盖与 DESTDIR 之争。

6. `strip sash` 是 Makefile 里的裸命令（非变量），交叉环境下**可执行**
   （profile [buildenv] 的 PATH 含 /data/service/hnp/bin，其中有 strip），
   但它会使 OHOS 的 ELF `.codesign` 签名失效，导致产物一执行就报
   `Operation not permitted`；故在 package() 里按仓内知识 E077 的
   "移除签名段 → 重签 → 恢复权限" 顺序修复（详见 _restore_ohos_codesign
   的 docstring 与 notes.md）。未给上游打补丁、未删改上游语义。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class SashConan(ConanFile):
    name = "sash"
    version = "3.8"
    description = ("sash is a stand-alone shell for system recovery which "
                   "includes built-in versions of many standard commands")
    license = "LicenseRef-sash-custom"
    homepage = "https://members.tip.net.au/~dbell/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一真实依赖：Makefile 的 LIBS = -lz（-gzip/-gunzip 内建命令）。
        # 登记表旧注"需 readline"经源码取证不成立：全树无 readline/history.h
        # 引用（只有 cmd_ed.c 的静态函数 readLines），故不声明该依赖。
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 把 profile [buildenv]（CONFIG_SHELL / PATH / LD_LIBRARY_PATH）带进
        # conanbuild：PATH 决定裸命令 make/strip 的解析，LD_LIBRARY_PATH 是
        # SDK lld 找 libxml2.so.16 的既知前提（见 ci/conan/profiles 注释）。
        env = VirtualBuildEnv(self)
        env.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器取自 Conan conf，绝不裸用 shell 的 ${CC}/${CFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # zlib 头/库搜索路径由 conan 依赖图给出（R26：禁硬编码系统路径）
        zlib = self.dependencies["zlib"]
        cppflags = " ".join(f"-I{d}" for d in zlib.cpp_info.includedirs)
        ldflags = " ".join(f"-L{d}" for d in zlib.cpp_info.libdirs)
        # 不追加 -static：见模块 docstring 第 2 点

        # 见模块 docstring 第 4 点：raw 串保字面反斜杠
        mount_opt = r"MOUNT_TYPE='\"ext3\"'"

        # R9：一律 -j1；-C 进源码目录（basic_layout 已分离 build 目录）
        self.run(
            f"make -C {self.source_folder} CC={cc} "
            f"HAVE_LINUX_ATTR=0 {mount_opt} "
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' -j1",
            env="conanbuild",
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "sash", src=self.source_folder, dst=bindir)
        copy(self, "sash.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        self._restore_ohos_codesign(os.path.join(bindir, "sash"))

    def _restore_ohos_codesign(self, target):
        """修复上游无条件 `strip` 造成的签名失效（鸿蒙内核加载期拒绝执行）。

        上游 Makefile 的 `sash:` 规则在链接之后紧跟一条裸 `strip sash`，而
        OHOS 要求 ELF 的 `.codesign` 段有效：strip 改写 ELF 后签名作废，执行
        时报 `Operation not permitted`（errno EPERM，shell rc=126），且与文件
        权限位无关。本机对照实验证据（同一 hello 程序）：
            strip 前 rc=0 → strip 后 rc=126 → 走下面三步 rc=0
        处置顺序取仓内知识 E077：必须先移除已失效的签名段，再重签
        （binary-sign-tool 拒绝覆盖已存在的段，会报 "section already exists"），
        最后恢复可执行位 —— 顺序不可交换。

        工具 llvm-objcopy / binary-sign-tool 由 profile [buildenv] 的 PATH
        提供（/data/service/hnp/bin），经 env="conanbuild" 注入，符合 R33
        （不裸用未定义的 shell 变量）。若某环境本就未生成 .codesign 段，
        Step1 的 --remove-section 是无害空操作。
        """
        path = target.replace("\\", "/")
        self.run(f"llvm-objcopy --remove-section .codesign '{path}'",
                 env="conanbuild")
        self.run(f"binary-sign-tool sign -inFile '{path}' -outFile '{path}'"
                 f" -selfSign 1", env="conanbuild")
        self.run(f"chmod a+x '{path}'", env="conanbuild")

    def package_info(self):
        # CLI 包：只暴露 bin/（R38 的 commands.json 在软件级目录）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
