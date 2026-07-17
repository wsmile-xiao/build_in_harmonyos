#!/usr/bin/env python3
"""Conan recipe — cimg 3.6.6 (C++ Template Image Processing Library).

CImg 是一个 header-only C++ 图像处理库，核心是单个头文件 CImg.h。
无需编译，安装方式为复制 CImg.h 到 include 目录。

Homebrew formula 参考:
  url "https://cimg.eu/files/CImg_3.6.6.zip"
  install: include.install "CImg.h"

可选依赖（不影响核心功能）:
  - X11: 图形显示（鸿蒙 PC 上缺失，通过 cimg_display=0 禁用）
  - libjpeg/libpng/libtiff: 图像格式支持
  - FFTW3: 快速傅里叶变换
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class CimgConan(ConanFile):
    name = "cimg"
    version = "3.6.6"
    description = "C++ Template Image Processing Library (header-only)"
    license = "CECILL-2.0"
    homepage = "https://cimg.eu/"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(self, "CImg.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "Licence*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CImg")
        self.cpp_info.set_property("cmake_target_name", "CImg::CImg")
        self.cpp_info.libs = []
