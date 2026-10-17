#!/usr/bin/env python3
"""Conan recipe — dnsdbq 2.6.8 (raw Makefile, command line tool).

dnsdbq — DNSDB 查询命令行工具（Farsight Security）。上游：
https://github.com/dnsdb/dnsdbq（Apache-2.0，C 语言，纯 Makefile 构建，
无 configure）。

HarmonyOS OHOS aarch64 适配要点：
- 纯 Makefile（非 autotools）：无 configure 步骤，直接 make。Makefile 通过
  JANSBASE/CURLINCL/CURLLIBS 变量注入依赖头/库路径，本配方把 jansson 与
  curl 的 package_folder 逐项注入（R49 私有 prefix 口径的 raw-make 变体）。
- asinfo.c 的解析器调用统一改用经典 POSIX 接口 res_init()/res_query()，
  错误码经 h_errno 暴露（配 hstrerror()）；补丁 0001 删除 BIND 风格
  res_n*() 族与全局 _res 的依赖，不持有 per-call resolver 状态，任何平台
  均走同一代码路径，无平台条件编译分支（见补丁 0001 与 notes.md）。
- Makefile 的 install 目标硬编码 /usr/local（无写权限），故 package() 手工
  复制 bin/dnsdbq 与 man 页到 package_folder（bti/acedb 同法）。
- 工具链：SDK clang 默认 target 即 aarch64-unknown-linux-ohos（无需
  --target/--sysroot），CC 从 profile conf tools.build:compiler_executables
  取得（R33：禁止裸用 ${CC}）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    chmod,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DnsdbqConan(ConanFile):
    name = "dnsdbq"
    version = "2.6.8"
    description = "DNSDB query tool (Farsight Security DNSDB client)"
    license = "Apache-2.0"
    homepage = "https://www.dnsdb.info/"
    url = "https://github.com/dnsdb/dnsdbq"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Makefile 链接 -ljansson 与 libcurl（curl-config），两者均已在 ohpcd
        # 制品仓发布（jansson/2.15.1.1、curl/8.15.0.1）；-lresolv 来自 OHOS
        # sysroot（libresolv.a），非 conan 依赖。
        self.requires("jansson/2.15.1.1")
        self.requires("curl/8.15.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 profile conf 取，禁止裸用 ${CC} 环境变量
        ccx = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccx.get("c", "clang")
        jansson_dep = self.dependencies["jansson"]
        curl_dep = self.dependencies["curl"]  # curl 依赖包引用，非外部 curl 命令
        # Makefile 变量注入：JANSBASE（jansson 基目录）、CURLINCL/CURLLIBS
        # （curl 头/库，替代 curl-config 探测——CI worker 无 curl-config）
        curlincl = "-I{}".format(curl_dep.package_folder + "/include")
        curllibs = "-L{} -lcurl".format(curl_dep.package_folder + "/lib")
        self.run(
            'make -j1 CC="{cc}" JANSBASE="{jansbase}" '
            'CURLINCL="{curlincl}" CURLLIBS="{curllibs}"'.format(
                cc=cc,
                jansbase=jansson_dep.package_folder,
                curlincl=curlincl,
                curllibs=curllibs,
            ),
            cwd=self.source_folder,
        )

    def package(self):
        # Makefile install 硬编码 /usr/local（无写权限）——手工打包
        bin_dir = os.path.join(self.package_folder, "bin")
        man1_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man1_dir, exist_ok=True)
        copy(self, "dnsdbq", self.source_folder, bin_dir, keep_path=False)
        chmod(self, os.path.join(bin_dir, "dnsdbq"), 0o755)
        # 上游 man 源文件名为 dnsdbq.man，安装后命名为 dnsdbq.1
        copy(self, "dnsdbq.man", self.source_folder, man1_dir, keep_path=False)
        man_src = os.path.join(man1_dir, "dnsdbq.man")
        man_dst = os.path.join(man1_dir, "dnsdbq.1")
        if os.path.exists(man_src) and not os.path.exists(man_dst):
            os.rename(man_src, man_dst)

    def package_info(self):
        # 纯可执行包：只交付 bin/（dnsdbq）+ share/man，无库供下游链接
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
