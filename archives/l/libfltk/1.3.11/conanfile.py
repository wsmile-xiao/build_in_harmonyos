#!/usr/bin/env python3
"""Conan recipe for libfltk 1.3.11 — CMake (C++).

FLTK (Fast Light Toolkit) — cross-platform C++ GUI toolkit.
X11 后端必需 libx11；可选 X 扩展库（Xinerama/Xfixes/Xcursor/Xft/
Xrender/GL）全部关闭以缩短依赖链；JPEG/PNG/ZLIB 用内置实现
（FLTK_USE_BUILTIN_*），不引入外部图像依赖。上游 test/ 目录为
demo 程序集合（FLTK_BUILD_TEST=ON 构建即验证编译链接）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FltkConan(ConanFile):
    name = "libfltk"
    version = "1.3.11"
    description = "FLTK — cross-platform C++ GUI toolkit"
    license = "LGPL-2.0-only"
    homepage = "https://www.fltk.org/"
    url = "https://github.com/fltk/fltk"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfltk supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # X11 后端必需 libx11（main 上已有 1.8.13 完整适配）；
        # Xext/Xinerama/Xcursor/Xft/Xrender 均为可选，不依赖
        self.requires("libx11/1.8.13")
        # xorgproto 提供 X11/X.h 等协议头（Xlib.h 内部 #include <X11/X.h>），
        # 作为 libx11 传递依赖会被 conan 标为 "Skipped binaries" 不装头文件，
        # 提升为直接 requires 强制安装（hyprpicker 传递依赖同款修复）
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 是 CMake 未知平台，UNIX 变量默认为 FALSE（log4cplus 先例），
        # FLTK 的 CMakeLists 用 if(NOT APPLE AND NOT WIN32) 分支查找 X11，
        # 且部分源文件依赖 if(UNIX)——统一置 TRUE
        tc.variables["UNIX"] = "TRUE"
        # 可选 X 扩展库全关闭（依赖链短，仓库未适配 Xinerama/Xcursor/Xft）
        tc.variables["OPTION_USE_XINERAMA"] = "OFF"
        tc.variables["OPTION_USE_XFIXES"] = "OFF"
        tc.variables["OPTION_USE_XCURSOR"] = "OFF"
        tc.variables["OPTION_USE_XFT"] = "OFF"
        tc.variables["OPTION_USE_XRENDER"] = "OFF"
        tc.variables["OPTION_USE_GL"] = "OFF"
        tc.variables["OPTION_CAIRO"] = "OFF"
        # 内置图像库（避免外部 zlib/libpng/libjpeg 依赖）
        tc.variables["FLTK_USE_SYSTEM_JPEG"] = "OFF"
        tc.variables["FLTK_USE_SYSTEM_PNG"] = "OFF"
        tc.variables["FLTK_USE_SYSTEM_ZLIB"] = "OFF"
        # 上游 test/ demo 程序：构建即验证编译链接（沙箱无 X display 无法运行）
        tc.variables["FLTK_BUILD_TEST"] = "ON"
        tc.variables["FLTK_BUILD_EXAMPLES"] = "OFF"
        # FindX11 模块查找 libX11：注入 libx11 包的 include/lib 路径
        #（变量名必须用 FindX11 模块的 X11_X11_INCLUDE_PATH / X11_X11_LIB；
        #  FLTK 的 options.cmake 找到 X11 后仅记录 -lX11 链接项，未把
        #  X11 include 加入编译命令——需额外用 -isystem 注入，否则
        #  FL/fl_utf8.h 的 #include <X11/Xlib.h> 编译失败）
        x11 = self.dependencies["libx11"]
        x11_base = x11.package_folder
        if x11_base:
            tc.variables["X11_X11_INCLUDE_PATH"] = os.path.join(x11_base, "include")
            tc.variables["X11_INCLUDE_PATH"] = os.path.join(x11_base, "include")
            # libx11 制品仓为 shared 构建（libX11.so），FindX11 经
            # CMAKE_LIBRARY_PATH 自动定位，无需硬编码 X11_X11_LIB
            tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(x11_base, "include")
            tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(x11_base, "lib")
            tc.extra_cflags.append(f"-isystem{os.path.join(x11_base, 'include')}")
            tc.extra_cxxflags.append(f"-isystem{os.path.join(x11_base, 'include')}")
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
                f"-L{os.path.join(x11_base, 'lib')} "
                f"{tc.variables.get('CMAKE_EXE_LINKER_FLAGS', '')}"
            )
        # xorgproto 提供 X11/X.h 协议头（Xlib.h 内部 include），注入 include 路径
        xorg = self.dependencies.get("xorgproto")
        if xorg and xorg.package_folder:
            tc.extra_cflags.append(f"-isystem{os.path.join(xorg.package_folder, 'include')}")
            tc.extra_cxxflags.append(f"-isystem{os.path.join(xorg.package_folder, 'include')}")
        # fluid（构建期代码生成工具）链接 libX11.so.6，运行时还依赖其传递
        # 库（libxcb/libXdmcp/libXau 等），把所有依赖 lib 目录注入
        # LD_LIBRARY_PATH（沙箱环境不会自动注入）
        lib_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib"))
        ]
        # OHOS SDK 的 lld 运行时依赖 libxml2.so.16（llvm/lib 目录），
        # CI Worker 上 LD_LIBRARY_PATH 未含该目录导致 clang 调用 lld 时
        # 编译器检测/链接失败（libxkbcommon #6310 同款问题），注入即可
        llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib"
        )
        if os.path.isdir(llvm_lib):
            lib_paths.append(llvm_lib)
        # 一次性注入（多次 save_script 同名会互相覆盖，丢失前面的注入）
        if lib_paths:
            env = Environment()
            env.append_path("LD_LIBRARY_PATH", os.pathsep.join(lib_paths))
            env.vars(self).save_script("conanbuild_env")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # fltk-config 脚本由 cmake install 一并安装到 bin/（FLTK 官方配置脚本）

    def package_info(self):
        # 静态库：fltk_images 依赖 fltk，图像格式用内置实现
        self.cpp_info.libs = ["fltk_images", "fltk"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "fltk")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m"]
