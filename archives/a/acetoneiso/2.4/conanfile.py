#!/usr/bin/env python3
"""Conan recipe — acetoneiso 2.4 (Qt6 qmake 工程，HarmonyOS PC aarch64 适配).

- 上游：Debian 官方源 acetoneiso_2.4.orig.tar.gz
- 构建：qmake + make（Qt6 Widgets 模块）
- 鸿蒙适配：QWebView/QtDBus/QtWebKit 在 OHOS 不可用，
  device_scan/media_available 改用 /dev 光驱扫描（__OHOS__ 分支）
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.build import stdcpp_library


class AcetoneisoConan(ConanFile):
    name = "acetoneiso"
    version = "2.4"
    description = "AcetoneISO — CD/DVD image management tool (Qt6, OHOS adapted)"
    license = "GPL-3.0"
    homepage = "https://sourceforge.net/projects/acetoneiso/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 base (Widgets 在 qtbase 包内)
        self.requires("qtbase/6.11.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # strip_root=True：去掉顶层 acetoneiso2.4/，使补丁路径 a/acetoneiso/... 匹配
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        import os
        qtbase = self.dependencies["qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake6")
        if not os.path.isfile(qmake):
            qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        qtlib = os.path.join(qtbase.package_folder, "lib")
        src = os.path.join(self.source_folder, "acetoneiso")
        # Qt6 工具链：qmake + make（R33: 不依赖未定义的 shell 环境变量）
        self.run(f'QT_INSTALL_LIBS="{qtlib}" {qmake} {src}/acetoneiso.pro', cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        import os
        import shutil
        # OHOS 限制：strip 后的 ELF 在 hmdfs 上无法执行（Operation not permitted），
        # 因此直接从构建产物复制未 strip 的二进制，绕过 make install 的 strip 环节。
        src = os.path.join(self.source_folder, "acetoneiso", "acetoneiso")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(bin_dir, "acetoneiso"))
        os.chmod(os.path.join(bin_dir, "acetoneiso"), 0o755)

    def package_info(self):
        import os
        # 可执行程序，无库文件供下游链接
        self.cpp_info.bindirs = ["bin"]
        # 可执行程序包：将 bin 目录注入运行环境 PATH（conan 2.x 用 runenv_info）
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
