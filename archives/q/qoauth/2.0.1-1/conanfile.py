#!/usr/bin/env python3
"""Conan recipe for qoauth 2.0.1-1 on OpenHarmony PC."""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

class QoauthConan(ConanFile):
    name = "qoauth"
    version = "2.0.1-1"
    description = "Qt OAuth library (Qt6, OHOS adapted)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/ayoy/qoauth"
    url = "https://github.com/ayoy/qoauth"
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    # 仅承诺 shared 构建：qmake 产物为 libqoauth.so*，不提供静态库目标，
    # 故不声明 shared/fPIC 选项（评审意见 #2：避免 shared=False 路径产出空包）

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qca/2.3.10")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 仅设置环境变量；qmake 必须在 build() 中打完补丁后执行（评审意见 #1：
        # generate() 先于 build() 运行，qmake 作用于未打补丁的 .pro 会丢失 QCA 路径）
        qca = self.dependencies["qca"]
        os.environ["QCA_INCLUDE"] = os.path.join(qca.package_folder, "include", "Qca-qt6")
        os.environ["QCA_LIB"] = os.path.join(qca.package_folder, "lib")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        qtbase = self.dependencies["qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        self.run(f"{qmake} {src}/qoauth.pro PREFIX={self.package_folder}", cwd=src)
        self.run(f"make -j{os.cpu_count()}", cwd=src)

    def package(self):
        src = self.source_folder
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "include", "QtOAuth"))
        copy(self, "*.pc", src=os.path.join(src, "lib", "pkgconfig"),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        # 实际产物为 libqoauth.so.2.0.0（soname libqoauth.so.2），故 libs=["qoauth"]
        self.cpp_info.libs = ["qoauth"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 注：qca 依赖传递：conan 2.29.1 下 cpp_info.requires=["qca"] 会被校验为
        # 内部组件引用（"internal components that are not defined"）而失败，
        # 故此处不声明跨包 requires；下游消费者请同时 requires qca/2.3.10
        # （QtCrypto 头路径由 qca 包的 includedirs 提供），参考 test_package/conanfile.py
