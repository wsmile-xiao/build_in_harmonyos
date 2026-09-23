#!/usr/bin/env python3
"""Conan 2 recipe — cramfsswap 1.4.5 (C CLI 工具, 依赖仅 zlib).

cramfsswap 把 cramfs 文件系统镜像在小端/大端字节序之间互换（含 superblock、
inode 位域、块指针的逐字段字节交换，并按 zlib crc32 重算镜像 CRC）。
产物: bin/cramfsswap。

上游事实（Debian native 包，Vcs = salsa.debian.org/debian/cramfsswap）：
- 纯手写 Makefile（非 autotools），单编译单元 cramfsswap.c，
  规则 `$(CC) -Wall -g -O $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o cramfsswap
  cramfsswap.c -lz`——CC/LD/CPPFLAGS/LDFLAGS 均可由 make 命令行变量覆盖。
- 依赖仅 zlib（debian/control Build-Depends: zlib1g-dev），镜像 CRC 用 crc32。
- linux/cramfs_fs.h（CRAMFS_MAGIC/struct cramfs_inode）与 byteswap.h 由
  OHOS NDK sysroot 直接提供（usr/include/linux/ 下齐全），无需平台分支。
- 上游测试 = debian autopkgtest test-cmd（mkfs.cramfs 生成镜像 → cramfsswap
  交换两次 → diff 断言「首换不同、再换复原」）。OHOS CI 环境无 util-linux
  的 mkfs.cramfs，test_package 以确定性 Python 夹具生成等价镜像运行同一
  语义断言（见 test_package/MANIFEST.yml）。

OHOS 适配（patches/0001-cramfsswap.c.patch，运行时分支、非条件编译）：
- 显式 #include <unistd.h>：read/write/lseek/close 原为隐式声明。
- argc==2 的 --version/-V/--help/-h 自报入口：上游无版本探针，CI L2
  冒烟探测四项全 rc!=0 会判 FAIL。
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class CramfsswapConan(ConanFile):
    name = "cramfsswap"
    version = "1.4.5"
    description = "cramfs 文件系统镜像小端/大端字节序互换工具 (cramfsswap)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/cramfsswap"
    url = "https://salsa.debian.org/debian/cramfsswap"
    topics = ("cramfs", "filesystem", "endianness", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 Build-Depends: zlib1g-dev → conan zlib/1.3.1.1（ohpcd 已发布，
        # OHOS armv8 缓存为静态 libz.a，链接进产物后运行时无额外 DT_NEEDED）
        self.requires("zlib/1.3.1.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cramfsswap is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        pass  # 单文件 make 直编：source_folder == build_folder，产物原地生成

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # zlib 的 -I/-L 注入 make 变量（上游规则把 CPPFLAGS/LDFLAGS 放在
        # 源文件之前、-lz 在最后，链接顺序正确）
        dep = self.dependencies["zlib"]
        self._zlib_inc = dep.cpp_info.includedirs[0]
        self._zlib_lib = dep.cpp_info.libdirs[0]

    def build(self):
        # R33: 编译器从 conan conf 取（CI 上 $CC 为空）；Makefile 的 LD 独立于
        # CC（上游 LD=cc），OHOS musl 工具链无裸 cc → CC/LD 都覆盖
        #（ondir 同型：只覆盖 CC 会让链接步找裸 cc 失败，Error 127）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        src = str(self.source_folder)
        bf = str(self.build_folder)

        # 只构建 `cramfsswap` 目标、跳过上游 `all` 里的 `strip`：hnp clang
        # 产物自带 .codesign 链接签名，strip 后签名与文件内容不再一致，
        # OHOS 内核拒绝执行（exec 报 Operation not permitted，rc=126，
        # 本任务实测复现：未 strip 的同文件可执行）。strip 也不参与
        # conan-verify L4（NX/PIE/RELRO 判据与是否 strip 无关）。
        self.run(
            f'make -C "{src}" cramfsswap CC="{cc}" LD="{cc}" '
            f'CPPFLAGS="-I{self._zlib_inc}" LDFLAGS="-L{self._zlib_lib}"',
            env="conanbuild",
        )
        copy(self, "cramfsswap", src=src, dst=bf)

        # 层1 smoke：自报版本入口（补丁新增）——rc=0 且含版本号
        self.run(f'"{bf}/cramfsswap" --version', env="conanbuild")

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        copy(self, "cramfsswap", src=self.build_folder,
             dst=os.path.join(pkg, "bin"))
        copy(self, "cramfsswap.1", src=src,
             dst=os.path.join(pkg, "share", "man", "man1"))
        copy(self, "COPYING", src=src,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
