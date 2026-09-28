#!/usr/bin/env python3
"""Conan recipe for fltk 1.4.5 — CMake (C++).

FLTK (Fast Light Toolkit) — 跨平台 C++ GUI 工具包，本包走 X11 后端。

1.4.x 相对仓库里已有的 libfltk/1.3.11 有几处会静默出错的差异：

* 构建选项整体改名（OPTION_USE_XINERAMA → FLTK_USE_XINERAMA、
  OPTION_CAIRO → FLTK_GRAPHICS_CAIRO、FLTK_USE_SYSTEM_JPEG →
  FLTK_USE_SYSTEM_LIBJPEG…）。沿用旧名 CMake 不报错，只会在 configure
  末尾给一句 "Manually-specified variables were not used"，于是选项
  "看起来传进去了、实际完全没生效"。
* 新增 FLTK_BACKEND_X11 / FLTK_BACKEND_WAYLAND 两个后端开关，后者在
  UNIX 上默认 ON，必须显式关掉（见 generate() 注释）。
* OpenGL 开关从 OPTION_USE_GL 变成 FLTK_BUILD_GL。
* 上游不再有 CTest 目标，test/ 只是一组独立 demo 程序；
  ``cmake --build . --target test`` 无效。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, rm


class FltkConan(ConanFile):
    name = "fltk"
    version = "1.4.5"
    description = "FLTK — cross-platform C++ GUI toolkit (X11 backend)"
    license = "LGPL-2.0-only"
    homepage = "https://www.fltk.org/"
    url = "https://github.com/fltk/fltk"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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
                f"fltk supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # X11 后端必需 libx11（main 上已有 1.8.13 完整适配）
        self.requires("libx11/1.8.13")
        # xorgproto 提供 X11/X.h 等协议头（Xlib.h 内部 #include <X11/X.h>），
        # 作为 libx11 传递依赖会被 conan 标为 "Skipped binaries" 不装头文件，
        # 提升为直接 requires 强制安装
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 是 CMake 未知平台，UNIX 变量默认为 FALSE（log4cplus 先例），
        # FLTK 的 CMakeLists 用 if(NOT APPLE AND NOT WIN32) 分支查找 X11，
        # 且部分源文件依赖 if(UNIX)——统一置 TRUE
        tc.variables["UNIX"] = "TRUE"
        # 后端二选一：开 X11、关 Wayland。FLTK_BACKEND_WAYLAND 在 UNIX 上
        # 默认 ON（options.cmake:280），保持开启会 pkg_check_modules 探测
        # wayland-client/wayland-cursor/wayland-protocols/xkbcommon：
        #   * 探测不到 → 自己把 FLTK_BACKEND_WAYLAND 静默置 0（构建"成功"
        #     但选项实际没生效，属于假通过）；
        #   * 探测到   → 强制 FLTK_GRAPHICS_CAIRO=TRUE，并要求 Xfixes/
        #     Xrender/Xft/Xcursor/Xinerama 头文件全存在，缺一个就
        #     FATAL_ERROR（本仓未适配这些扩展，必炸）。
        # 显式 OFF 可完全绕开这条分支；FLTK_BACKEND_X11 在 UNIX 上默认已 ON，
        # 仍显式写出以免上游改默认值。
        tc.variables["FLTK_BACKEND_X11"] = "ON"
        tc.variables["FLTK_BACKEND_WAYLAND"] = "OFF"
        # 可选 X 扩展库全关闭（仓库未适配 Xinerama/Xfixes/Xcursor/Xft/Xrender）
        tc.variables["FLTK_USE_XINERAMA"] = "OFF"
        tc.variables["FLTK_USE_XFIXES"] = "OFF"
        tc.variables["FLTK_USE_XCURSOR"] = "OFF"
        tc.variables["FLTK_USE_XFT"] = "OFF"
        tc.variables["FLTK_USE_XRENDER"] = "OFF"
        tc.variables["FLTK_USE_PANGO"] = "OFF"
        tc.variables["FLTK_GRAPHICS_CAIRO"] = "OFF"
        tc.variables["FLTK_OPTION_CAIRO_WINDOW"] = "OFF"
        tc.variables["FLTK_OPTION_CAIRO_EXT"] = "OFF"
        # OpenGL：OHOS 上无 libGL，显式关闭。注意该 option 只在
        # HAVE_GL（resources.cmake 扫到 LIB_GL/LIB_MesaGL）为真时才被
        # 声明，未声明时传值只会多一条 unused-variable 警告，不影响构建。
        tc.variables["FLTK_BUILD_GL"] = "OFF"
        # 内置图像库（避免外部 zlib/libpng/libjpeg 依赖）
        tc.variables["FLTK_USE_SYSTEM_LIBJPEG"] = "OFF"
        tc.variables["FLTK_USE_SYSTEM_LIBPNG"] = "OFF"
        tc.variables["FLTK_USE_SYSTEM_ZLIB"] = "OFF"
        # 1.4.x 恒建静态库；该开关只是"额外再建一份 shared"
        tc.variables["FLTK_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游 test/ demo 程序：顶层构建（FLTK_IS_TOPLEVEL）默认 ON，
        # 构建即验证编译链接（沙箱无 X display 无法运行）
        tc.variables["FLTK_BUILD_TEST"] = "ON"
        tc.variables["FLTK_BUILD_EXAMPLES"] = "OFF"
        # FindX11 模块查找 libX11：注入 libx11 包的 include/lib 路径
        #（变量名必须用 FindX11 模块的 X11_X11_INCLUDE_PATH；FLTK 1.4.5
        #  的 src/CMakeLists.txt:694 会把 X11_INCLUDE_DIR 追加进
        #  OPTIONAL_INCLUDES，但 configure 阶段仍需 CMAKE_LIBRARY_PATH
        #  才能定位 libX11.so）
        x11 = self.dependencies["libx11"]
        x11_base = x11.package_folder
        if x11_base:
            tc.variables["X11_X11_INCLUDE_PATH"] = os.path.join(x11_base, "include")
            tc.variables["X11_INCLUDE_PATH"] = os.path.join(x11_base, "include")
            tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(x11_base, "include")
            tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(x11_base, "lib")
            tc.extra_cflags.append(f"-isystem{os.path.join(x11_base, 'include')}")
            tc.extra_cxxflags.append(f"-isystem{os.path.join(x11_base, 'include')}")
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
                f"-L{os.path.join(x11_base, 'lib')} "
                f"{tc.variables.get('CMAKE_EXE_LINKER_FLAGS', '')}"
            )
        # xorgproto 提供 X11/X.h 协议头（Xlib.h 内部 include），注入 include 路径
        xorg_base = self.dependencies["xorgproto"].package_folder
        if xorg_base:
            tc.extra_cflags.append(f"-isystem{os.path.join(xorg_base, 'include')}")
            tc.extra_cxxflags.append(f"-isystem{os.path.join(xorg_base, 'include')}")
        # fluid（构建期代码生成工具，FLTK_BUILD_FLUID 默认 ON）链接
        # libX11.so.6，运行时还依赖其传递库，把所有依赖 lib 目录注入
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

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # fltk-options / fltk-config / fluid 由 cmake install 安装到 bin/
        if self.options.shared:
            # FLTK_BUILD_SHARED_LIBS 是"额外"语义，打开时会同时留下 .a，
            # 这里删掉静态库让包语义单一（消费侧不再可能出现"以为用 .so
            # 实际链了 .a"的混淆）
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # 全静态。链接顺序 = 依赖顺序：
        #   fltk_images 同时 PUBLIC 依赖 fltk、fltk_png、fltk_jpeg（src/CMakeLists.txt:846,905-907）
        #   fltk_png 又 PUBLIC 依赖 fltk_z（png/CMakeLists.txt:101）
        # 三者都是上游随包内置编译的独立静态库（FLTK_USE_SYSTEM_* 全为 OFF），
        # 漏掉任何一个，用到图像 API 的消费者都会在链接期拿到未定义符号。
        self.cpp_info.libs = ["fltk_images", "fltk_png", "fltk_jpeg", "fltk_z", "fltk"]
        # 内置 png/jpeg/zlib 的头文件装在 include/FL/images（上游 fltk::images
        # 的 INSTALL_INTERFACE 也是这个目录），一并作为 include 根暴露
        self.cpp_info.includedirs = ["include", os.path.join("include", "FL", "images")]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "fltk")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m"]
