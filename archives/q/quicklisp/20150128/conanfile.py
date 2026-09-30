#!/usr/bin/env python3
"""Conan recipe for quicklisp 20150128 — Quicklisp bootstrap (quickstart) file.

quicklisp 是 Common Lisp 的库管理器。上游仓库 quicklisp/quicklisp-bootstrap 只
分发一个自包含启动文件 quicklisp.lisp（57144 bytes）；按其头注释，用法是
「启动 Lisp，然后 (load "quicklisp.lisp")」。源码包无 C/C++ 源码、无可编译产物
（Debian 源码包 Architecture: all，构建系统仅 debhelper/dh）。

本配方按 SKILL v12.21「无构建/打包族」模板变体 B/C（纯数据/脚本重分发）适配：
  * 不定义 build()——上游 `make all` 是空目标（Makefile 只有 all:/tag:），
    无编译可做；禁止用伪造编译日志假装"构建"（R34）。
  * package() 只安装 quicklisp.lisp + README.txt + LICENSE.txt + OHOS 运行期
    环境辅助脚本到包内 share/quicklisp/。
  * package_id() 清空——内容与 os/compiler/build_type/arch 完全无关，
    单一 package_id 服务所有 OHOS 架构（与 Debian Architecture: all 一致）。
  * package_info() 用 runenv/buildenv 暴露 QUICKLISP_BOOTSTRAP，消费者无需猜测
    包内路径即可在 Common Lisp 中 (load (uiop:getenv "QUICKLISP_BOOTSTRAP"))。

鸿蒙（OHOS）相关改动（详见 notes.md 与 ohos/quicklisp-ohos-env.sh）：
  * quicklisp.lisp 的 client 默认安装目录由
    (merge-pathnames "quicklisp/" (user-homedir-pathname)) 导出（quicklisp.lisp:1571），
    依赖实现能解析出 HOME。OpenHarmony PC 默认用户目录为 /storage/Users/currentUser，
    但沙箱/服务方式拉起的进程可能没有 HOME，导致安装目录不可预期。辅助脚本
    quicklisp-ohos-env.sh 统一导出 QUICKLISP_BOOTSTRAP / QUICKLISP_HOME，并在
    HOME 缺失时回退到 OHOS 默认用户目录。
  * 包产物无 ELF（纯文本 .lisp），因此无需 ELF 签名（与可执行包不同）。
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class QuicklispConan(ConanFile):
    name = "quicklisp"
    version = "20150128"
    description = ("Quicklisp: library manager for Common Lisp — the self-contained "
                   "bootstrap/quickstart file quicklisp.lisp (loads the Quicklisp client)")
    license = "MIT"
    homepage = "https://www.quicklisp.org"
    url = "https://github.com/quicklisp/quicklisp-bootstrap"

    # 纯数据/脚本重分发：无编译产物、无 C/C++ 头或库。
    # settings 四项保留用于交叉编译矩阵的一致性校验（L0p）。
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # OHOS 运行期环境辅助脚本随配方导出，再由 package() 装进包内。
        copy(self, "ohos/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 本库无编译步骤：上游 Makefile 的 `all:` 是空目标，无 C/C++ 源码。
        # 这里只执行标准的补丁应用（conandata.yml `patches: []` 时为空操作），
        # 不调用任何编译器、不伪造编译日志（R34）。
        apply_conandata_patches(self)

    def package(self):
        # 启动文件与说明文档（上游 install 目标即把 quicklisp.lisp 装到
        # /usr/share/common-lisp/source/quicklisp；此处装到包内 share/quicklisp/）
        copy(self, "quicklisp.lisp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "quicklisp"))
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "quicklisp"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # OHOS 运行期环境辅助脚本
        copy(self, "quicklisp-ohos-env.sh",
             src=os.path.join(self.source_folder, "ohos"),
             dst=os.path.join(self.package_folder, "share", "quicklisp"))

    def package_id(self):
        # 内容是架构无关的 Common Lisp 源文件 → 单一 package_id
        self.info.clear()

    def package_info(self):
        resource_dir = os.path.join(self.package_folder, "share", "quicklisp")
        bootstrap = os.path.join(resource_dir, "quicklisp.lisp")
        # 无 C/C++ 产物：清空默认目录，仅保留数据资源目录
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        # 运行期/构建期暴露启动文件绝对路径（消费者：(load (uiop:getenv "QUICKLISP_BOOTSTRAP"))）
        self.runenv_info.define_path("QUICKLISP_BOOTSTRAP", bootstrap)
        self.buildenv_info.define_path("QUICKLISP_BOOTSTRAP", bootstrap)
