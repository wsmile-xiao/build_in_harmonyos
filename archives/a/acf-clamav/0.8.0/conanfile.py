#!/usr/bin/env python3
"""Conan recipe — acf-clamav 0.8.0 (Alpine Configuration Framework module).

纯 Lua ACF 应用模块（同 acf-freeradius3/acf-apk-tools 先例）：单个递归
Makefile 复制 Lua controller/model 与 HTML 模板(.lsp) 到
/usr/share/acf/app/clamav 布局。source() 用 git clone（archive 端点被
GitLab 418 反爬拦截，git 智能 HTTP 端点可用，R39 官方源保留）。
运行时依赖 acf-core（ACF 框架 mvc.lua 分发）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AcfClamavConan(ConanFile):
    name = "acf-clamav"
    version = "0.8.0"
    description = "Alpine Configuration Framework clamav module — web-based admin for ClamAV"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-clamav"
    url = "https://gitlab.alpinelinux.org/acf/acf-clamav"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 运行时框架依赖（acf-core 提供 mvc.lua 分发），同 acf-apk-tools 先例
        self.requires("acf-core/0.24.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # archive 端点被 GitLab 418 反爬拦截 → git clone（git 智能 HTTP 可用）
        self.run(
            f"git clone --depth 1 --branch {self.conan_data['sources']['git_branch']} "
            f"{self.conan_data['sources']['url']} _src_tmp",
            cwd=self.source_folder,
        )
        import shutil, os
        for item in os.listdir(os.path.join(self.source_folder, "_src_tmp")):
            shutil.move(
                os.path.join(self.source_folder, "_src_tmp", item),
                os.path.join(self.source_folder, item),
            )
        shutil.rmtree(os.path.join(self.source_folder, "_src_tmp"), ignore_errors=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-clamav does not support os={self.settings.os}")
        apply_conandata_patches(self)
        # make all 是 no-op（校验 Makefile 语法），同先例
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        # make install DESTDIR=<pkg> 复制到 <pkg>/usr/share/acf/app/clamav
        self.run(
            f"make -C {self.source_folder} install DESTDIR={self.package_folder} -j1",
            env="conanbuild",
        )

    def package_info(self):
        # 纯 Lua 模块：无 libs/bindirs，暴露 resdir 供 acf-core 分发
        self.cpp_info.resdirs = ["usr/share/acf/app/clamav"]
        self.cpp_info.bindirs = []
