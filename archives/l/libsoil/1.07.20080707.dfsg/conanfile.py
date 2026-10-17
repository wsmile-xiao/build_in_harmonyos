#!/usr/bin/env python3
"""Conan recipe — libsoil 1.07.20080707.dfsg (SOIL - Simple OpenGL Image Library)

纯 C 静态库，无 conan 依赖。
构建系统：上游纯 Makefile（projects/makefile/makefile，无 configure/CMake）。
OHOS 适配：
  - SOIL.c 的 OGL 纹理上传函数依赖 <GL/gl.h>/<GL/glx.h>（OHOS 无 GL 头文件/运行时），
    由补丁引入 SOIL_NO_GL 特性宏编译掉 OGL 函数，保留纯图像解码/编码 API
    （SOIL_load_image / SOIL_load_image_from_memory / SOIL_save_image / ...）。
  - makefile 默认 CXX=gcc（OHOS 无 gcc）且 CXXFLAGS 含 -s（strip，无用且干扰符号），
    构建时覆盖 CXX=clang、CXXFLAGS="-O2 -Wall -DSOIL_NO_GL"，并在 make 前 mkdir obj。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibsoilConan(ConanFile):
    name = "libsoil"
    version = "1.07.20080707.dfsg"
    description = "SOIL - Simple OpenGL Image Library (image load/save API for HarmonyOS)"
    license = "MIT"
    homepage = "https://www.lonesock.net/soil.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C 库，无 conan 依赖（R26：系统无同名 libSOIL，默认即可）
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 获取，禁止裸用 ${CC}
        cc = self.conf.get("tools.build:compiler_executables", check_type=dict, default={}).get("c", "clang")
        # 上游 makefile：CXX=gcc、CXXFLAGS=-O2 -s -Wall、OBJDIR=obj（不存在）
        # 覆盖 CXX/CXXFLAGS（去掉 -s strip，注入 SOIL_NO_GL），先 mkdir obj
        make_dir = os.path.join(self.source_folder, "projects", "makefile")
        self.run("mkdir -p obj", cwd=make_dir)
        self.run(
            'make CXX={cc} CXXFLAGS="-O2 -Wall -DSOIL_NO_GL" -j1'.format(cc=cc),
            cwd=make_dir,
        )

    def package(self):
        # 静态库产物：projects/makefile 的 ../../lib/libSOIL.a
        copy(self, "libSOIL.a",
             os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "lib"))
        # 公共头：src/SOIL.h
        copy(self, "SOIL.h",
             os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        # libSOIL.a -> 链接名 SOIL
        self.cpp_info.libs = ["SOIL"]
