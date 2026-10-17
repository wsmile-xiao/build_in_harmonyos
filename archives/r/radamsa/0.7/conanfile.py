#!/usr/bin/env python3
"""Conan 2 recipe — radamsa 0.7（Aki Helin / OUSPG，通用型模糊测试工具，零依赖）.

radamsa 是黑盒模糊测试器（test case generator）。上游构建形态特殊：核心逻辑
以 Scheme 编写（rad/*.scm），需要先用 Owl Lisp 引导编译器把 Scheme 生成成单个
C 文件 radamsa.c，再用 cc 编译成最终单文件可执行 radamsa（无外部运行时依赖）。
即上游 Makefile 的两段式：`bin/ol -O1 -o radamsa.c rad/main.scm` → `cc -o bin/radamsa radamsa.c`。

OHOS 适配要点：
- 三份输入全部预置（主 tarball + Owl Lisp 引导 ol-0.2.2.c.gz + (lib hex core)
  库归档），消除上游 Makefile 的构建期网络行为（wget OWLURL、git clone hex）。
- 生成器 bin/ol 由 ol-0.2.2.c.gz 用设备 clang 现场编译（上游 Makefile bin/ol 目标同型）。
- patches/0001 作用于**构建期生成物 radamsa.c**（生成后、编译前应用）：OHOS 上
  /dev/null、/dev/zero 等字符设备 poll(2)/select(2) 永不报告写就绪，Owl VM 向
  stdout 写前以无限超时 poll 写就绪 → 上游 README 与 tests/1k.sh 的标准用法
  `radamsa ... -n 1000 - > /dev/null` 永久挂起。补丁把写集中的字符设备 fd 直接
  视为可写（实测修复；管道/套接字保持原生 poll 语义）。
- 生成产物 radamsa.c 字节级确定（两次独立构建 sha256 一致），补丁可稳定套用。
- tests/run 等上游测试由 test_package 之外的平台验证流程执行（见 reports/）；
  build() 内仅做 smoke（--version）。
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get, download, export_conandata_patches


class RadamsaConan(ConanFile):
    name = "radamsa"
    version = "0.7"
    description = "通用型黑盒模糊测试工具（test case generator for robustness testing）"
    license = "MIT"
    homepage = "https://gitlab.com/akihe/radamsa"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fuzzer", "security", "testing", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # radamsa 是单文件 CLI 工具（无库产物），无 shared/static 选项（R26 不适用：
    # 非系统同名库）。

    no_copy_source = True

    def export_sources(self):
        # conandata patches 段登记的 0001 补丁随配方导出（L0q 要求 patches/ 可导出）。
        # 注意：本配方不能在 build() 起始调用 apply_conandata_patches()——该补丁的
        # 目标文件 radamsa.c 是构建中间生成物，必须等 build() 内生成步完成后套用。
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        # 主源码：radamsa-v0.7.tar.gz（去掉顶层 radamsa-v0.7/）
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Owl Lisp 引导源与 hex 库归档：download() 保留原件（.gz 内含的顶层目录/
        # 符号链接按上游布局由 build() 显式解包还原），sha256 由 download 校验
        owl = self.conan_data["owl_bootstrap"][self.version]
        download(self, owl["url"], filename="ol-0.2.2.c.gz", sha256=owl["sha256"])
        hexlib = self.conan_data["hex_library"][self.version]
        download(self, hexlib["url"], filename="hex-e95ebd38.tar.gz",
                 sha256=hexlib["sha256"])

    def build(self):
        # R33: 编译器从 conan conf 取（CI 上 $CC 为空）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        src = str(self.source_folder)

        # 1) 还原上游 Makefile 的输入布局：
        #    ol.c（OWLURL 引导源）+ lib/hex/（(lib hex core) 库，上游 Makefile
        #    通过 git clone 取得，此处由预置归档解包，规避构建期网络）
        self.run('gzip -dc ol-0.2.2.c.gz > ol.c', cwd=src, env="conanbuild")
        self.run('mkdir -p lib bin && tar -xzf hex-e95ebd38.tar.gz -C lib',
                 cwd=src, env="conanbuild")
        # API 归档端点的顶层目录为 hex-<sha>-<sha>（见 conandata.yml 注）
        self.run('mv lib/hex-e95ebd38e4f7ef8e3d4e653f432e43ce0a804ca6-e95ebd38e4f7ef8e3d4e653f432e43ce0a804ca6 lib/hex',
                 cwd=src, env="conanbuild")

        # 2) 引导编译器：cc 编译 Owl Lisp VM（上游 Makefile `bin/ol: ol.c` 同型）
        self.run(f'"{cc}" -O2 -o bin/ol ol.c', cwd=src, env="conanbuild")

        # 3) 生成步：Scheme → C（上游 Makefile `radamsa.c: rad/*.scm` 的生成规则）
        self.run('bin/ol -O1 -o radamsa.c rad/main.scm', cwd=src, env="conanbuild")

        # 4) OHOS 平台补丁：作用于刚生成的 radamsa.c（生成后、编译前）
        self.run('patch -p1 < patches/0001-radamsa-do_poll-ohos-chardev-writable.patch',
                 cwd=src, env="conanbuild")

        # 5) 最终编译：单文件可执行（上游 Makefile `bin/radamsa: radamsa.c` 同型）
        self.run(f'"{cc}" -O2 -o bin/radamsa radamsa.c', cwd=src, env="conanbuild")

        # 层1 smoke：单二进制自证（完整上游 tests/ 套件由平台验证流程执行并留档）
        self.run('bin/radamsa --version', cwd=src, env="conanbuild")

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        copy(self, "radamsa", src=os.path.join(src, "bin"),
             dst=os.path.join(pkg, "bin"))
        # man 页：上游 install 用 `gzip -9`（带时间戳、不可复现），此处安装未压缩
        # 原件 doc/radamsa.1，内容等价（同 Homebrew 处理理由：可复现性）
        copy(self, "radamsa.1", src=os.path.join(src, "doc"),
             dst=os.path.join(pkg, "share", "man", "man1"))
        copy(self, "LICENCE", src=src, dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
