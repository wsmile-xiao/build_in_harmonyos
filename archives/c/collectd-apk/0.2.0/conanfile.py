#!/usr/bin/env python3
"""Conan recipe — collectd-apk 0.2.0 (Makefile, collectd 插件)

collectd 的 apk-tools 插件：收集 Alpine 包管理器管理的包信息并输出指标。
本配方构建 apk.so 插件（collectd LoadPlugin apk 加载）。

构建要点（jirutka/collectd-apk 的 Makefile）：
  - COLLECTD_INCLUDE_DIR 默认 /usr/include/collectd/core，需命令行覆盖为
    collectd 头文件包（本仓库 archives/c/collectd/5.12.0）的 include/collectd/core
  - 用 pkg-config 取 apk（apk-tools）与 json-c 的 cflags/libs：
    经 PkgConfigDeps 生成 .pc 到 generators，PKG_CONFIG_PATH 指向 generators
  - make build 输出 apk.so；上游 check 目标需真实 collectd 二进制 + apk
    环境（Alpine 专用），OHOS 无法执行，如实记录
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class CollectdApkConan(ConanFile):
    name = "collectd-apk"
    version = "0.2.0"
    description = "Collectd plugin for apk-tools"
    license = "GPL-2.0-only"
    homepage = "https://github.com/jirutka/collectd-apk"
    url = "https://github.com/jirutka/collectd-apk"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验，否则报
    # "Package type is 'library', but no 'shared' option declared"——
    # cattle 同款问题先例）；apk.so 插件是共享模块，声明但默认静态偏好
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # 插件 API 头文件（daemon/plugin.h）+ libapk + json-c
        self.requires("collectd/5.12.0")
        self.requires("apk-tools/2.14.4")
        self.requires("json-c/0.17")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成 apk.pc / json-c.pc 到 generators，PKG_CONFIG 可解析
        PkgConfigDeps(self).generate()
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("conanbuild_env")

    def build(self):
        # 参照 apk-tools 方案：不用 conan self.run（OHOS 沙箱 conanbuild env
        # 下 make 会 SIGSEGV），用 subprocess 干净环境 + 显式 PKG_CONFIG_PATH
        # 指向 generators（apk.pc / json-c.pc），pkg-config 才能解析 apk/json-c
        import subprocess
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "clang")
        collectd_inc = os.path.join(
            self.dependencies["collectd"].package_folder,
            "include", "collectd", "core")
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:/system/bin:/usr/bin:/bin"
        env["PKG_CONFIG_PATH"] = self.generators_folder
        # json-c 0.17 头文件在 include/json-c/ 子目录，而 apk.c 用
        # `#include <json.h>`（旧式 json-c 风格）：Makefile 的 JSONC_CFLAGS
        # 走 pkg-config（-Iinclude，找不到 json.h），用 make 命令行变量
        # 覆盖为 -I<include/json-c> 让 <json.h> 可解析
        jsonc_inc = os.path.join(
            self.dependencies["json-c"].package_folder,
            "include", "json-c")
        cmd = (f"make -C {self.source_folder} build "
               f"CC={cc} COLLECTD_INCLUDE_DIR={collectd_inc} "
               f"JSONC_CFLAGS=-I{jsonc_inc}")
        r = subprocess.run(cmd, shell=True, cwd=self.source_folder,
                           env=env, capture_output=True, text=True, timeout=600)
        print(r.stdout[-4000:])
        if r.returncode != 0:
            print(r.stderr[-2000:])
            raise ConanException(f"collectd-apk make failed: rc={r.returncode}")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        copy(self, "apk.so",
             src=os.path.join(src, "build"),
             dst=os.path.join(pkg, "lib", "collectd"))
        copy(self, "LICENSE", src=src,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
