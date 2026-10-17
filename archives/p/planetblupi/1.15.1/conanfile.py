#!/usr/bin/env python3
"""Conan recipe for planetblupi 1.15.1 — HarmonyOS PC (aarch64, SDL2/Wayland).

Planet Blupi 是开源策略游戏（C++/CMake, SDL2 系）。构建链依赖：
  SDL2 + SDL2_image + SDL2_ttf + SDL2_mixer（制品仓均有）
  + sdl-kitchensink（ffmpeg 视频播放，制品仓 1.0.13）
  + argagg（命令行解析，制品仓 0.4.7）
  + gettext/Intl + Iconv（musl libc 内置，CMake 探测需注入）

适配要点（HarmonyOS OHOS musl）：
  1. CMake 的 find_package(Intl) 在 musl 下探测 libintl 失败（功能在 libc
     内），经 CMAKE_HAVE_LIBC_INTL 预置绕过
  2. harfbuzz 版本冲突（sdl-kitchensink→14.2.0 vs sdl2-ttf→14.2.0.1.1.2）
     经 profile [replace_requires] 统一为 14.2.0
  3. 游戏资源（resources/）随包安装，运行时按相对路径查找
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PlanetblupiConan(ConanFile):
    name = "planetblupi"
    version = "1.15.1"
    description = "Planet Blupi - A delirious spell-binding game (SDL2 strategy game)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/blupi-games/planetblupi"
    url = "https://github.com/blupi-games/planetblupi"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("sdl2-image/2.8.12")
        self.requires("sdl2-ttf/2.24.0")
        self.requires("sdl2-mixer/2.8.2")
        self.requires("sdl-kitchensink/1.0.13")
        self.requires("argagg/0.4.7")
        # musl libc 不含 gettext 运行库：上游 CMakeLists find_package(Intl)
        # 强制要求 Intl_LIBRARY/Intl_INCLUDE_DIR，加 gettext 包并在 generate()
        # 里把探测变量钉到该包
        self.requires("gettext/0.22.5")
        # harfbuzz 双版本冲突（sdl-kitchensink 链 ffmpeg→libass→harfbuzz/14.2.0
        # vs sdl2-ttf→harfbuzz/14.2.0.1.1.2）：配方内 override 统一为 14.2.0，
        # 不依赖 CI profile 的 [replace_requires]（CI profile 不可改）
        self.requires("harfbuzz/14.2.0", override=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # SDL2 系依赖的包头在包内 include/SDL2/ 子目录，而上游源码用平铺形式
        # #include "SDL_image.h"/<SDL.h>/<SDL_stdinc.h>——CMakeDeps 只注入
        # include/，不含子目录，CI 上 SDL_image.h/SDL.h not found。
        # 经 CPATH 追加各依赖包 include/SDL2 子目录补齐平铺查找路径（R33：显式
        # 注入，不依赖未定义 shell 变量）。
        env = Environment()
        cpaths = []
        for dep_name in ("sdl2", "sdl2-image", "sdl2-ttf", "sdl2-mixer"):
            dep_pkg = self.dependencies[dep_name].package_folder
            sub = os.path.join(dep_pkg, "include", "SDL2")
            if os.path.isdir(sub):
                cpaths.append(sub)
        # argagg 包 cpp_info 未正确声明 include 目录（头在 include/argagg/ 下，
        # 上游 #include <argagg/argagg.hpp> 需 -I include）
        argagg_inc = self.dependencies["argagg"].cpp_info.includedirs
        if argagg_inc:
            cpaths.append(argagg_inc[0])
        if cpaths:
            # 用 buildenv 而非临时 env.vars().apply()：buildenv 会写入
            # conanbuildenv 并在 build 助手（cmake.configure/build）执行时生效
            self.buildenv.define("CPATH", os.pathsep.join(cpaths))
        # musl libc 不含 gettext（Intl）也不导出 pthread_setcanceltype 等
        # GNU 扩展；CMake 4.x 的 FindIntl 强制要求 Intl_LIBRARY，需注入
        # gettext 包（含 libintl.h/libintl.so）与探测覆盖
        tc.variables["CMAKE_HAVE_LIBC_INTL"] = True
        # FindIntl 强制要求 Intl_LIBRARY/Intl_INCLUDE_DIR：钉到 conan gettext 包
        gettext = self.dependencies["gettext"].cpp_info
        tc.variables["Intl_INCLUDE_DIR"] = gettext.includedirs[0]
        tc.variables["Intl_LIBRARY"] = os.path.join(gettext.libdirs[0], "libintl.a")
        # 上游 CMakeLists 用自带 Find 模块的变量链接（${SDL2_LIBRARIES}/
        # ${Intl_LIBRARIES} 等），而 CMakeDeps 只提供 target——变量为空导致
        # SDL 主库与 libintl 未链入（CI 链接错误 libintl_textdomain/SDL_* undefined）。
        # 把各变量直接钉到 conan 包内的实际库文件。
        intl_lib = tc.variables["Intl_LIBRARY"]
        tc.variables["Intl_LIBRARIES"] = intl_lib
        tc.variables["Intl_FOUND"] = True
        sdl_deps = {
            "SDL2_LIBRARIES": ("sdl2", "libSDL2.a"),
            "SDL2_IMAGE_LIBRARIES": ("sdl2-image", "libSDL2_image.a"),
            "SDL2_TTF_LIBRARIES": ("sdl2-ttf", "libSDL2_ttf.a"),
            "SDL2_MIXER_LIBRARIES": ("sdl2-mixer", "libSDL2_mixer.a"),
        }
        for var, (dep_name, lib_name) in sdl_deps.items():
            dep = self.dependencies[dep_name]
            lib_path = os.path.join(dep.package_folder, "lib", lib_name)
            if os.path.isfile(lib_path):
                tc.variables[var] = lib_path
            # include 路径同步钉入（上游 include_directories(${SDL2_INCLUDE_DIRS})）
            inc_sub = os.path.join(dep.package_folder, "include", "SDL2")
            if os.path.isdir(inc_sub):
                tc.variables[var.replace("LIBRARIES", "INCLUDE_DIRS")] = inc_sub
        # SDLKitchensink_LIBRARIES 钉到 CMakeDeps 声明的 target（静态库
        # libSDL_kitchensink_static.a 的 ffmpeg/tiff/webp 传递依赖由 target
        # 自动展开，手工枚举静态链顺序不可维护）
        tc.variables["SDLKitchensink_LIBRARIES"] = "sdl_kitchensink::sdl_kitchensink"
        # 上游自带 FindIconv 强制要求 Iconv_INCLUDE_DIR：musl libc 内置 iconv
        # （无独立库，Iconv_LIBRARY 可选），头文件在 OHOS SDK sysroot。
        # SDK 根从 profile 的编译器路径推导（/data/service/hnp/bin/clang），
        # sysroot 经 glob 定位（版本号不写死）
        sysroot = self.conf.get("tools.build:sysroot", default="")
        if not sysroot:
            clang = (self.conf.get("tools.build:compiler_executables", default={},
                                    check_type=dict) or {}).get("c", "")
            hnp_root = os.path.dirname(os.path.dirname(clang)) if clang else "/data/service/hnp"
            hits = sorted(glob.glob(os.path.join(
                hnp_root, "ohos-sdk.org", "*", "ohos", "native", "sysroot")))
            sysroot = hits[-1] if hits else ""
        if sysroot:
            tc.variables["Iconv_INCLUDE_DIR"] = os.path.join(sysroot, "usr", "include")
        tc.variables["Iconv_IS_BUILT_IN"] = True
        # 上游 CMakeLists.txt:2 用旧版 cmake_minimum_required(<3.5)，CMake 4.x
        # 已移除兼容性，需显式放行
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["Intl_IS_BUILTIN"] = False
        tc.variables["Iconv_IS_BUILT_IN"] = True
        # PB_HTTP_VERSION_CHECK 关闭（避免 libcurl 依赖，默认 OFF）
        tc.variables["PB_HTTP_VERSION_CHECK"] = False
        # 上游 CMake 会找 msgfmt/msgmerge 生成 .gmo 翻译文件（OHOS hnp 自带）
        tc.variables["GETTEXT_MSGFMT_EXECUTABLE"] = "/data/service/hnp/bin/msgfmt"
        tc.variables["GETTEXT_MSGMERGE_EXECUTABLE"] = (
            "/data/service/hnp/gettext.org/gettext_0.26/bin/msgmerge")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM 必须以命令行缓存变量传入：该检查在
        # cmake_minimum_required() 处理时执行，早于 toolchain 文件加载
        # （project() 时），toolchain 变量与环境变量均不可达
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "planetblupi", src=os.path.join(self.build_folder),
             dst=os.path.join(self.package_folder, "bin"))
        # 游戏资源（关卡/音效/图形），运行时按 share 相对路径查找
        copy(self, "*", src=os.path.join(self.source_folder, "resources"),
             dst=os.path.join(self.package_folder, "share", "planetblupi", "resources"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
