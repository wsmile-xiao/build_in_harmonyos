#!/usr/bin/env python3
"""Conan recipe — c-turtle 1.0.5 (header-only).

上游 C-Turtle 是 Python Turtle 的 header-only C++ 移植：仓库无构建系统
（无 CMake/Makefile/configure），头文件即库本体。CTurtle.hpp 公开头相对
`#include "CImg.h"`（上游把 CImg 3.1MB 单头 vendored 在仓库根目录），
因此 package() 必须把 CTurtle.hpp 与 CImg.h 一并装入 include/（与
knowledge/drafts/DRAFT-gli-0.8.2.0-headeronly-ship-bundled-dep-headers
同族：header-only 库的依赖是头文件级依赖，vendored 依赖头必须随包分发）。
无编译阶段；消费者必须在包含 CTurtle.hpp 前定义 CTURTLE_HEADLESS
（headless 模式，CImg cimg_display=0，无需 X11/图形栈）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CTurtleConan(ConanFile):
    name = "c-turtle"
    version = "1.0.5"
    description = "C-Turtle: A header-only port of Python's Turtle graphics library to C++"
    license = "MIT"
    homepage = "https://github.com/walkerje/C-Turtle"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 无编译阶段：build() 仅应用配方补丁（conandata patches 为空集），
    # 不得伪造编译日志——R34；header-only 库无编译产物。
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # 主库头 + 内置依赖头（CTurtle.hpp 相对 include "CImg.h"，必须同目录）
        copy(self, "CTurtle.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "CImg.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only：无构建依赖 → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []