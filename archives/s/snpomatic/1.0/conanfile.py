#!/usr/bin/env python3
"""Conan recipe for snpomatic 1.0 (SNP-o-matic short-read mapper, Magnus Manske).

上游: https://github.com/magnusmanske/snpomatic  —— tag v1.0
构建系统: 裸 Makefile（15 个文件，无 configure、无 autotools）

台账复验结论（本配方据此定形，全部为设备实测，非引用候选描述）:
  * 上游 Makefile 既没有 all 目标，也没有 install 目标，更没有文档/man 生成步骤；
    默认目标就是文件里第一条规则 findknownsnps（Makefile:13）。所谓
    "文档链需要 asciidoctor 与 antiword" 只存在于 Debian 的 debian/rules
    (override_dh_installdocs / override_dh_installman)，与本 tarball 无关，
    因此这里既没有需要关掉的文档目标，也没有需要绕开的生成步骤。
  * LIBS=-lm（Makefile:4），#include 全集只有 STL + POSIX（stdio/stdlib/string/
    unistd/getopt/time/sys/types/sys-stat），零第三方编译依赖 ⇒ requires 为空。
  * 上游 tag 归档与 Debian snpomatic_1.0.orig.tar.gz 逐字节相同（同为 66546 B、
    sha256 相同、cmp 无差异），故 sources.url 直接写官方 tag，sha256 未改动。
  * 上游五个目标里 ungap 在 tag v1.0 源码不自洽：src/ungap.cpp:261 以 4 个实参
    调用 5 参函数 align_solexa_paired（声明 src/snpomatic.h:179，无默认实参），
    任何符合标准的 C++ 编译器都报 "too few arguments to function call"；
    上游 master 至今未修（同一行原样）。这是上游缺陷，不是平台缺陷 ⇒
    不打补丁、不改源码、不吞错误，只把可编译的四个程序列为构建目标，
    并把证据与 Debian 的 fix_ungap 下游补丁一起写进 notes.md 披露。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout

# 构建目标 = 上游 Makefile 里在本 tag 真能编译通过的四个程序
BINARIES = ("findknownsnps", "reassemble", "variety", "mapcontigs")


class SnpomaticConan(ConanFile):
    name = "snpomatic"
    version = "1.0"
    description = ("SNP-o-matic: stringent short-read mapping and SNP detection "
                   "suite (findknownsnps, reassemble, variety, mapcontigs)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/magnusmanske/snpomatic"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 字面判据：本包零补丁（conandata.yml patches: []），
        # 这里导出的是"空补丁集"，不做出"已应用补丁"的暗示。
        export_conandata_patches(self)

    def requirements(self):
        # W0/R36：上游 LIBS=-lm，无第三方编译依赖 ⇒ 无 requires。
        pass

    def layout(self):
        basic_layout(self)

    # R32: settings.os 判断必须覆盖 Linux 与 OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("os=%s not supported" % self.settings.os)

    def source(self):
        get(self, **self.conandata_sources(), strip_root=True)

    def conandata_sources(self):
        return self.conan_data["sources"]

    # R33: 编译器只从 Conan conf 取，绝不裸用 $CXX/$CFLAGS
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        # 零补丁：此调用是空操作（patches 为空列表），保留字面判据。
        apply_conandata_patches(self)
        # tools.build:compiler_executables 在本仓是字典型 conf，且键名是 cpp；
        # 模板里的 :c 单项写法在 Conan 2.29.1 会抛 "does not exist in
        # configuration list"（在池先例见 notes.md 路径 B 节）。
        comps = self.conf.get("tools.build:compiler_executables",
                              default={}, check_type=dict) or {}
        cxx = comps.get("cpp") or "clang++"
        # 上游无 all/install 目标 ⇒ 必须显式枚举构建目标（bare make 只会得到
        # findknownsnps 一个程序）。CXX 走命令行覆盖（make 命令行变量优先于
        # Makefile 内赋值），其余 CXXFLAGS/-g -O3 与链接行一律照上游原样。
        with chdir(self, self.source_folder):
            self.run('make CXX="%s" -j1 %s' % (cxx, " ".join(BINARIES)))

    def package(self):
        # 上游没有 install 目标（也不依赖 coreutils install，E174 家族）⇒
        # 手工 copy 产物；OHOS 上没有 install(1)。
        bindir = os.path.join(self.package_folder, "bin")
        for prog in BINARIES:
            copy(self, prog, self.source_folder, bindir, keep_path=False)
        copy(self, "gpl-3.0.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "Manual.doc", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "doc", "snpomatic"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
