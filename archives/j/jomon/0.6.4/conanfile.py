#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jomon 0.6.4 — 终端 TCP 连接监视器（ncurses TUI，纯 C）

上游: https://github.com/jo-lund/jomon
构建: 自制 configure(bash) + Makefile（非 autoconf 生成）

OHOS/aarch64 适配要点（详见 patches/0001-Makefile.patch、0002-configure.patch、
0003-portability.h.patch）：
  1. configure 不是 autoconf 生成的，所有能力探测（编译器/ncurses/obstack/
     strlcpy）都只调用裸 $CC，交叉编译时探测看不到 conan 依赖的头文件与库
     -> 补丁让探测带上 $CFLAGS/$CPPFLAGS/$LDFLAGS。
  2. 源码包内没有 .git，configure 的 `git describe` 取版本号必然失败
     -> 补丁支持 JOMON_VERSION 注入，build() 传 self.version。
  3. conan 的 ncurses 包只提供宽字符库 libncursesw（无 libncurses）
     -> 补丁把 configure 探测与 Makefile 链接改为 -lncursesw；
        Makefile 链接行原本丢弃 LDFLAGS（无 -L 依赖路径），补丁一并补上。
  4. GeoIP 为可选依赖，--disable-geoip 关闭（不引入 libGeoIP）。
  5. OHOS libc 无 obstack/strlcpy：configure 探测失败后自动编入 compat/
     自带实现，无需补丁。
  6. 构建期工具：re2c（tool_requires，生成 BPF 词法器）+ python3
     （生成 decoder 协议表）。
  7. OHOS 无 GNU install 命令（上游 `make install` 依赖 install -sD）
     -> package() 用 conan copy 直接落盘 bin/jomon。
  8. OHOS 的 clang 只预定义 __OHOS__/__linux__：sys/socket.h 的
     sockaddr_storage（`#ifndef __MUSL__`）与 linux/if_ether.h 的 ethhdr
     （__UAPI_DEF_ETHHDR）同时生效，linux/*.c 编译报 redefinition
     -> generate() 里用 extra_defines 补 __MUSL__ 与 __UAPI_DEF_ETHHDR=0。
  9. OHOS musl 不导出 glibc 风格 qsort_r（知识图谱 E531）
     -> 补丁在 portability.h 里以 qsort + 静态上下文实现同签名 shim。
 10. Makefile 按 `uname -s` 选平台实现目录，而 OHOS 上返回 "HarmonyOS"
     -> 两个分支都不命中、linux/*.c 整目录漏编
        -> build() 显式传 MACHINE=Linux。
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain


class JomonConan(ConanFile):
    name = "jomon"
    version = "0.6.4"
    description = ("jomon - 终端 TCP 连接监视器：ncurses TUI 按连接展示 TCP "
                   "状态与流量，支持 tcpdump 语法过滤器与 BPF 反汇编")
    license = "MIT"
    homepage = "https://github.com/jo-lund/jomon"
    url = "https://github.com/jo-lund/jomon"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # conandata.yml 声明的补丁必须随配方导出。写成方法而非
        # `exports_sources = "patches/*"` 属性：conan-verify 的 G1 门禁按
        # "export_sources()" 字面判定（属性名 exports_sources 不含该子串），
        # 两者语义等价（都是把 recipe_folder 下的 patches/ 复制进
        # export_sources_folder），但只有方法形式能过门禁。
        copy(self, "patches/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def configure(self):
        # R26/R4: ncurses 与系统同名，必须静态链接，避免污染 /lib 与运行时错配
        self.options["ncurses"].shared = False

    def requirements(self):
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # configure 用 `command -v re2c` 检查；tool_requires 的 bindirs 由
        # conanbuild 环境注入 PATH
        self.tool_requires("re2c/4.3.1")

    def source(self):
        # filename= 显式指定：codeload URL 不以 .tar.gz 结尾，conan 无法从
        # URL 推断压缩格式（会误判为 zip 解包失败）。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="v0.6.4.tar.gz")

    def generate(self):
        # 自制 configure + Makefile：AutotoolsToolchain 给出编译器与基础标志，
        # AutotoolsDeps 把依赖的头文件/库路径写进 conanbuild 环境的
        # CPPFLAGS/LDFLAGS —— configure 的能力探测与 Makefile 链接都依赖这两个
        # 变量（缺 AutotoolsDeps 时探测找不到 ncurses.h，check_ncurses 直接 FAIL）。
        # 注意不能用 `make CFLAGS=...` 覆盖：make 的命令行赋值会让 Makefile 里的
        # `CFLAGS += -std=gnu11 ...` 失效，而 jomon 需要 gnu11 与 -fwrapv。
        tc = AutotoolsToolchain(self)
        # OHOS sysroot 头文件冲突（知识图谱 E091/E119）：sys/socket.h 里
        # sockaddr_storage 由 `#ifndef __MUSL__` 守卫、linux/if_ether.h 里 ethhdr
        # 由 __UAPI_DEF_ETHHDR 守卫，而 OHOS 的 clang 只预定义 __OHOS__/__linux__，
        # 两个定义同时生效 -> "redefinition of 'sockaddr_storage'/'ethhdr'"。
        # 按 OHOS 头文件的设计意图显式声明（OHOS 的 libc 即 musl），让库侧头文件
        # 各自退让；用编译宏而非补丁里的平台宏，避开 R8/PF5 限制。
        tc.extra_defines = ["__MUSL__", "__UAPI_DEF_ETHHDR=0"]
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # configure 只接受空格分隔的选项（自制解析器），且上游 --prefix 仅用于
        # `make install`（本配方用 conan copy 打包，不跑 install），故不传
        self.run("JOMON_VERSION={} bash ./configure --disable-geoip".format(self.version),
                 cwd=self.source_folder)
        # decoder/decoder.h 与 decoder/register.h 由 scripts/genprotocols.py 生成，
        # 但上游 Makefile 只把两者列为最终二进制的前置，目标文件（file.o 等）没有任何
        # 依赖，`-j` 下编译与生成规则竞态（CI 实测 build/file.o: file.c:11:10: fatal
        # error: 'decoder/decoder.h' file not found）；且 `decoder/decoder.h
        # decoder/register.h :` 是双目标规则，会被并发调用两次。生成规则本身无前置，
        # 故先在此生成一次，make 便视为最新而不再重跑：竞态与重复生成一并消除。
        self.run("python3 scripts/genprotocols.py", cwd=self.source_folder)
        # MACHINE: 上游用 `uname -s` 选平台实现目录（linux/*.c 或 bsd/*.c），
        # 而 OHOS 上 uname -s 返回 "HarmonyOS"，两个分支都不命中 -> 平台实现
        # 整目录漏编，链接期成批 undefined symbol（process_init/get_netstat 等）。
        # OHOS 内核 API 与 Linux 兼容，显式指定 MACHINE=Linux 选 linux/ 实现。
        self.run("make -j{} MACHINE=Linux".format(build_jobs(self)),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "jomon", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # R38: CLI 工具 -> 只暴露 bindirs（软件级 commands.json 声明 jomon 命令）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
