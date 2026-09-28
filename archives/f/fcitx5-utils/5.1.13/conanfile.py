#!/usr/bin/env python3
"""Conan recipe — fcitx5-utils 5.1.13.

fcitx5-utils 是 fcitx5 源码树内的 `Fcitx5Utils` 组件（src/lib/fcitx-utils/），
没有独立的上游发布仓库。上游归档来自 fcitx5 官方 tag 5.1.13
(https://github.com/fcitx/fcitx5/archive/refs/tags/5.1.13.tar.gz)。
本配方只打包该组件：输出 Fcitx5Utils 动态库、头文件、Fcitx5UtilsConfig.cmake /
Fcitx5UtilsConfigVersion.cmake、Fcitx5Utils.pc，使父库能用
find_package(Fcitx5Utils 5.1.13 REQUIRED) 命中 Fcitx5::Utils 目标。
不打包 fcitx5 core/module 等其他组件（任务边界：另立独立任务）。

构建方式：上游组件 CMakeLists 设计为从 fcitx5 顶层并入，本配方用独立的
wrapper CMakeLists.txt（staging 根 + add_subdirectory 组件目录）等价复刻
顶层所需的最小上下文：ECM(ecm_setup_version)、CMAKE_MODULE_PATH 指向
原树 cmake/（FindDL/FindLibIntl/FindPthread）、FCITX_INSTALL_* 变量、
config.h 生成、ENABLE_DBUS=Off、FCITX_EVENT_LOOP_BACKEND=none（OHOS 无
libuv/systemd 依赖，event_none.cpp 内置实现）。不改动任何上游源文件。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Fcitx5UtilsConan(ConanFile):
    name = "fcitx5-utils"
    version = "5.1.13"
    description = "Fcitx5Utils library (fcitx-utils component from fcitx5 source tree)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/fcitx/fcitx5"
    url = "https://github.com/fcitx/fcitx5"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # CMakeToolchain 在 generate() 中手动实例化（需设置 OHOS CMAKE_SYSROOT），
    # 故此处只声明 CMakeDeps。
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ECM 仅构建期需要（ecm_setup_version），作为构建依赖引入
        self.tool_requires("extra-cmake-modules/6.19.0")
        # i18n.cpp 使用 gettext/dgettext；OHOS libc 无 dgettext，sysroot 的
        # libintl.h 是空壳（无声明），必须依赖 gettext 包的真实 libintl
        # （FindLibIntl 依赖 libintl.h + libintl）。
        self.requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    @property
    def _staging_dir(self):
        # staging 由 source() 在 self.source_folder 下创建；W3/CI 的 conan create
        # 在缓存复用场景可能不重跑 source()（实例属性不跨进程），必须用
        # source_folder 确定性推导，不能依赖 self.* 实例状态。
        return os.path.join(self.source_folder, "staging")

    def generate(self):
        tc = CMakeToolchain(self)
        # Fcitx5CompilerSettings 要求 C++20；CI profile 可能是 cppstd=17。
        # 注意：不能只靠 tc.variables["CMAKE_CXX_STANDARD"]=20 —— toolchain 的
        # cppstd 块先用普通 set() 写 17（普通变量遮蔽 CACHE 变量），必须直接
        # 覆盖 cppstd 块（ada-url/async_simple 先例）。
        if self.settings.compiler.cppstd != "20":
            tc.blocks["cppstd"].values = {"cppstd": "20", "cppstd_extensions": "OFF"}
        # OHOS：CMAKE_SYSROOT 必须显式设置，否则 FindDL/FindPthread 等
        # find_path/find_library 搜不到 sysroot 下的 dlfcn.h/pthread.h
        # （编译器默认 sysroot 只影响编译，不影响 find_* 命令），
        # 参考 asmjit/bluez-qt 等仓库先例，从 OHOS SDK 自动发现 sysroot。
        if self.settings.os == "OHOS":
            import glob as _glob
            sdk_native = sorted(
                _glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native"))
            if sdk_native:
                sysroot = os.path.join(sdk_native[-1], "sysroot")
                tc.variables["CMAKE_SYSROOT"] = sysroot
                self.output.info("OHOS CMAKE_SYSROOT = %s" % sysroot)
        # OHOS sysroot 的 libintl.h 是空壳（无 gettext/bindtextdomain 声明），
        # FindLibIntl 的 find_path 会先命中 sysroot 而非 gettext 包。强制
        # LibIntl_INCLUDE_DIR/LIBRARY 指向 gettext 包的真实 libintl（头+库）。
        gettext_pkg = self.dependencies.get("gettext")
        if gettext_pkg and gettext_pkg.package_folder:
            tc.cache_variables["LibIntl_INCLUDE_DIR"] = os.path.join(
                gettext_pkg.package_folder, "include")
            tc.cache_variables["LibIntl_LIBRARY"] = os.path.join(
                gettext_pkg.package_folder, "lib", "libintl.a")
        tc.generate()

    def _stage_component(self):
        """把上游 fcitx5 树中的 Fcitx5Utils 组件整理为独立构建根 staging。

        staging 布局（等价复刻顶层 CMake 上下文）：
          staging/CMakeLists.txt           # 本配方生成的 wrapper
          staging/config.h.in              # 原树顶层 config.h.in（configure_file 生成 config.h）
          staging/cmake/                   # 原树顶层 cmake/（FindDL/FindLibIntl/FindPthread/
                                           #   Fcitx5CompilerSettings.cmake 等 find 模块）
          staging/fcitx-utils/             # 原树 src/lib/fcitx-utils/（组件本体，零改动）
        """
        src_root = self.source_folder
        fcitx5_root = self.source_folder  # strip_root=True：源码直接在 source 根
        staging = os.path.join(src_root, "staging")

        # 组件源码（原样复制，不改动）
        copy(self, "*", os.path.join(fcitx5_root, "src/lib/fcitx-utils"),
             os.path.join(staging, "fcitx-utils"))
        # 顶层 cmake/ find 模块 + 编译器设置
        copy(self, "*", os.path.join(fcitx5_root, "cmake"),
             os.path.join(staging, "cmake"))
        # config.h.in（组件源码 include "config.h"，由 wrapper configure_file 生成）
        copy(self, "config.h.in", fcitx5_root, staging)

        wrapper = """# 由 fcitx5-utils conanfile.py 生成的独立构建 wrapper。
# 等价复刻 fcitx5 顶层 CMakeLists 中 Fcitx5Utils 组件所需的上下文，
# 不改动任何上游源文件。
cmake_minimum_required(VERSION 3.16)
project(fcitx5-utils VERSION 5.1.13 LANGUAGES C CXX)

# ECM：ecm_setup_version 需要（Fcitx5UtilsConfigVersion.cmake）
find_package(ECM REQUIRED 1.0.0)
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake" ${ECM_MODULE_PATH} ${CMAKE_MODULE_PATH})
include(ECMSetupVersion)

include(Fcitx5CompilerSettings)
include(GNUInstallDirs)
# 组件 CMakeLists 使用 generate_export_header 与 configure_package_config_file
include(GenerateExportHeader)
include(CMakePackageConfigHelpers)

# 顶层 CMakeLists 定义的 FCITX_INSTALL_* 变量（Fcitx5UtilsConfig.cmake.in 用到）
set(FCITX_INSTALL_PREFIX ${CMAKE_INSTALL_PREFIX})
set(FCITX_INSTALL_SYSCONFDIR ${CMAKE_INSTALL_FULL_SYSCONFDIR})
set(FCITX_INSTALL_INCLUDEDIR ${CMAKE_INSTALL_FULL_INCLUDEDIR})
set(FCITX_INSTALL_LIBDIR ${CMAKE_INSTALL_FULL_LIBDIR})
set(FCITX_INSTALL_LIBDATADIR ${CMAKE_INSTALL_FULL_LIBDATADIR})
set(FCITX_INSTALL_LIBEXECDIR ${CMAKE_INSTALL_FULL_LIBEXECDIR})
set(FCITX_INSTALL_DATADIR ${CMAKE_INSTALL_FULL_DATADIR})
set(FCITX_INSTALL_PKGDATADIR "${CMAKE_INSTALL_FULL_DATADIR}/fcitx5")
set(FCITX_INSTALL_BINDIR ${CMAKE_INSTALL_FULL_BINDIR})
set(FCITX_INSTALL_LOCALEDIR ${CMAKE_INSTALL_FULL_LOCALEDIR})
set(FCITX_INSTALL_ADDONDIR "${CMAKE_INSTALL_FULL_LIBDIR}/fcitx5")
set(FCITX_INSTALL_CMAKECONFIG_DIR "${CMAKE_INSTALL_FULL_LIBDIR}/cmake")
set(FCITX_INSTALL_MODULE_HEADER_DIR "${CMAKE_INSTALL_FULL_INCLUDEDIR}/Fcitx5/Module/fcitx-module")

# 组件构建选项：OHOS 无 dbus/libuv/systemd 需求，取最小闭包
option(ENABLE_DBUS "Enable DBus" Off)
set(EVENT_LOOP_BACKEND "none" CACHE STRING "Event loop backend: auto/systemd/libuv/none")
set(FCITX_EVENT_LOOP_BACKEND "none")

# config.h 生成（组件源码 include "config.h"）
include(CheckFunctionExists)
include(CheckIncludeFile)
include(CheckCXXCompilerFlag)
check_function_exists(pipe2 HAVE_PIPE2)
check_include_file(sys/wait.h HAVE_SYS_WAIT_H)
check_include_file(sys/mman.h HAVE_SYS_MMAN_H)
check_include_file(sys/uio.h HAVE_SYS_UIO_H)
check_cxx_compiler_flag(-Wno-deprecated-declarations HAVE_NO_DEPRECATED_DECLARATIONS)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.h.in ${CMAKE_CURRENT_BINARY_DIR}/config.h)
include_directories(${CMAKE_CURRENT_BINARY_DIR})

# Fcitx5Utils 链接依赖：DL/LibIntl/Pthread（OHOS sysroot 提供 dlfcn.h / pthread.h；
# LibIntl 由 gettext 包提供真实 libintl）
# CMake 不识别 HarmonyOS 平台（System is unknown to cmake），交叉模式下
# find_path 不会自动搜索 sysroot，须显式把 sysroot include 加入 CMAKE_INCLUDE_PATH。
if(CMAKE_SYSROOT)
    list(APPEND CMAKE_INCLUDE_PATH "${CMAKE_SYSROOT}/usr/include")
endif()
find_package(DL REQUIRED)
find_package(LibIntl REQUIRED)
find_package(Pthread REQUIRED)

add_subdirectory(fcitx-utils)
"""
        with open(os.path.join(staging, "CMakeLists.txt"), "w") as f:
            f.write(wrapper)
        return staging

    def source(self):
        # strip_root=True：tarball 顶层目录 fcitx5-5.1.13 被剥掉，
        # 源码直接落在 source 根，patch (a/ 前缀 -p1) 与 staging 引用路径才正确
        get(self, **self.conan_data["sources"], strip_root=True)
        # OHOS libc++ 裁剪 C++20 <ranges>：先应用兼容补丁（标准 std::transform/copy 替换），
        # 再整理 staging（確保补丁进入构建源）
        apply_conandata_patches(self)
        # fcitx5 顶层需要 ECM/pkg-config 等大量依赖；本配方只构建 Fcitx5Utils 组件，
        # 用 staging 隔离（零上游改动）。_staging_dir 为只读属性（由 source_folder
        # 推导），此处不赋值。
        self._stage_component()

    def build(self):
        cmake = CMake(self)
        cmake.configure(cli_args=["-S", self._staging_dir])
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（仓库先例）
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        # 组件 CMakeLists 自带完整 install 规则（TARGETS/EXPORT/Config/pc/头文件），
        # 用 cmake.install() 生成标准布局：lib/libFcitx5Utils.so*、
        # include/Fcitx5/Utils/fcitx-utils/*.h、lib/cmake/Fcitx5Utils/*、
        # lib/pkgconfig/Fcitx5Utils.pc
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["Fcitx5Utils"]
        # 头文件按上游布局安装在 include/Fcitx5/Utils/fcitx-utils，
        # 消费者 include <fcitx-utils/...> 需要该 include 前缀
        self.cpp_info.includedirs = ["include/Fcitx5/Utils"]
        self.cpp_info.set_property("cmake_file_name", "Fcitx5Utils")
        self.cpp_info.set_property("cmake_target_name", "Fcitx5::Utils")
        # 生成 Fcitx5UtilsConfig.cmake 与 Fcitx5Utils.pc，父库 find_package 可命中
        self.cpp_info.set_property("pkg_config_name", "Fcitx5Utils")