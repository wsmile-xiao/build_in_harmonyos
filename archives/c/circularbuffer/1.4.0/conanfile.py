#!/usr/bin/env python3
"""Conan recipe — CircularBuffer 1.4.0 (header-only template library).

CircularBuffer 是 AgileWare/Roberto Lo Giacco 开发的 Arduino 风格
环形缓冲模板库（LIFO/FIFO），纯头文件实现（CircularBuffer.hpp 声明 +
CircularBuffer.tpp 实现 + CircularBuffer.h 兼容包装头），无任何构建系统，
无编译产物。本配方仅打包头文件，不定义 build()（R34：不得伪造编译日志）。
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CircularbufferConan(ConanFile):
    name = "circularbuffer"
    version = "1.4.0"
    description = "Arduino circular buffer library (LIFO/FIFO template library)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/rlogiacco/CircularBuffer"
    url = ""  # CI fills this

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL（/refs/tags/1.4.0）无文件扩展名，conan get() 无法
        # 从 URL 推断压缩格式，必须显式指定 filename（.tar.gz 后缀）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="circularbuffer-1.4.0.tar.gz")

    # 无编译阶段：不定义 build()（header-only 库，R34 不伪造编译日志）

    def package(self):
        # 参考仓库成功配方（broker/autobahn-cpp）：src/dst 使用绝对路径，
        # 相对路径 dst 在此环境下不被解析到 package_folder
        copy(self, "*.h", src=self.source_folder,
             dst=self.package_folder + "/include")
        # CircularBuffer.tpp 被 CircularBuffer.hpp 以 #include <CircularBuffer.tpp>
        # 方式包含，必须随头文件一起安装
        copy(self, "*.hpp", src=self.source_folder,
             dst=self.package_folder + "/include")
        copy(self, "*.tpp", src=self.source_folder,
             dst=self.package_folder + "/include")
        copy(self, "LICENSE*", src=self.source_folder,
             dst=self.package_folder + "/licenses", keep_path=False)

    def package_id(self):
        # 无构建依赖 os/compiler → 单一 package_id
        self.info.clear()

    def package_info(self):
        # 标准头文件信息：无 lib 无 bin
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
