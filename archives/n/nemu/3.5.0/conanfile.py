#!/usr/bin/env python3
"""Conan recipe for nemu 3.5.0 on HarmonyOS PC.

The recipe builds the CMake-based terminal virtual machine manager.
QEMU integration (embedded QEMU build) is disabled: nemu spawns
qemu-system-* binaries at runtime; on OHOS the qemu_bin_path is
configured by the user (test_package exercises the command-line
generation path).

Upstream test matrix (.github/workflows/tests.yml) enables
NM_WITH_USB=ON (OVF/OVA import is ON by default); the USB and OVF
features are required for the upstream integration tests, so both are
enabled here with conan-provided libusb + libudev-zero. D-Bus,
remote control and network map stay off (they need glib/dbus and
graphviz stacks which are out of scope and do not affect the QEMU
command line asserted by the tests).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import VirtualBuildEnv


class NemuConan(ConanFile):
    name = "nemu"
    version = "3.5.0"
    description = "nemu 3.5.0"
    license = "MIT"
    homepage = "https://github.com/nemuTUI/nemu"
    url = "https://github.com/nemuTUI/nemu"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("sqlite/3.53.3")
        self.requires("json-c/0.18")
        self.requires("gettext/0.22.5.1")
        self.requires("libxml2/2.15.3")
        self.requires("libarchive/3.7.7")
        self.requires("openssl/3.5.6.1")
        # NM_WITH_USB=ON（上游 tests.yml 同参）：libusb + libudev
        self.requires("libusb/1.0.27")
        self.requires("libudev-zero/1.0.4")
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # json-c 走上游 pkg_check_modules(JSONC REQUIRED json-c)：
        # PkgConfigDeps 生成 json-c.pc；其余 CMake find_package 走 CMakeDeps。
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()
        deps = CMakeDeps(self)
        # 上游 find_package 名与 conan 包名对齐：
        #   Sqlite3 -> sqlite, Intl -> gettext, LibXml2 -> libxml2,
        #   LibArchive -> libarchive, libusb-1.0 -> libusb, UDev -> libudev-zero
        # cmake_find_mode=both：同时生成 CONFIG 文件与 MODULE 变量
        # （上游 target_link_libraries 用 ${SQLITE3_LIBRARIES} 等
        #   MODULE 风格变量，纯 CONFIG 声明 target 不填这些变量）。
        deps.set_property("sqlite", "cmake_file_name", "Sqlite3")
        deps.set_property("sqlite", "cmake_target_name", "Sqlite::Sqlite3")
        deps.set_property("sqlite", "cmake_find_mode", "both")
        deps.set_property("gettext", "cmake_file_name", "Intl")
        deps.set_property("gettext", "cmake_target_name", "Intl::Intl")
        deps.set_property("gettext", "cmake_find_mode", "both")
        deps.set_property("libxml2", "cmake_file_name", "LibXml2")
        deps.set_property("libxml2", "cmake_target_name", "LibXml2::LibXml2")
        deps.set_property("libxml2", "cmake_find_mode", "both")
        deps.set_property("libarchive", "cmake_file_name", "LibArchive")
        deps.set_property("libarchive", "cmake_target_name", "LibArchive::LibArchive")
        deps.set_property("libarchive", "cmake_find_mode", "both")
        deps.set_property("libudev-zero", "cmake_file_name", "UDev")
        deps.set_property("libudev-zero", "cmake_target_name", "UDev::UDev")
        deps.set_property("libudev-zero", "cmake_find_mode", "both")
        # 上游引用 LIBUSB_1_LIBRARIES / LIBUSB_1_INCLUDE_DIRS（前缀 LIBUSB_1）
        deps.set_property("libusb", "cmake_file_name", "libusb-1.0")
        deps.set_property("libusb", "cmake_target_name", "libusb-1.0::libusb-1.0")
        deps.set_property("libusb", "cmake_find_mode", "both")
        deps.set_property("libusb", "cmake_additional_variables_prefixes", ["LIBUSB_1"])
        deps.generate()

        VirtualBuildEnv(self).generate()
        tc = CMakeToolchain(self)
        # 上游 tests.yml 构建矩阵：NM_WITH_USB=ON（OVF 默认 ON）。
        # D-Bus/remote/network-map 关闭（glib/dbus/graphviz 超出适配范围，
        # 且不影响测试断言的 QEMU 命令行）。
        tc.variables["NM_WITH_OVF_SUPPORT"] = True
        tc.variables["NM_WITH_DBUS"] = False
        tc.variables["NM_WITH_NETWORK_MAP"] = False
        tc.variables["NM_WITH_REMOTE"] = False
        tc.variables["NM_WITH_USB"] = True
        tc.variables["NM_WITH_QEMU"] = False
        tc.variables["NM_WITH_NCURSES"] = False
        ncurses = self.dependencies["ncurses"]
        tc.variables["CURSES_NCURSES_INCLUDE_PATH"] = os.path.join(
            ncurses.package_folder, "include")
        tc.variables["CURSES_INCLUDE_PATH"] = os.path.join(
            ncurses.package_folder, "include")
        # MODULE 式 FindSqlite3 的 FIND_PATH(SQLITE3_INCLUDE_DIR sqlite3.h)
        # 在交叉 sysroot 无系统 sqlite 头文件时落空，显式指向 conan 包。
        tc.cache_variables["SQLITE3_INCLUDE_DIR"] = os.path.join(
            self.dependencies["sqlite"].package_folder, "include")
        # 同理：OVF/USB 的 include_directories 变量（上游用 MODULE 变量名）。
        tc.cache_variables["LIBXML2_INCLUDE_DIR"] = os.path.join(
            self.dependencies["libxml2"].package_folder, "include", "libxml2")
        tc.cache_variables["LibArchive_INCLUDE_DIR"] = os.path.join(
            self.dependencies["libarchive"].package_folder, "include")
        tc.cache_variables["UDEV_INCLUDE_DIR"] = os.path.join(
            self.dependencies["libudev-zero"].package_folder, "include")
        tc.cache_variables["LIBUSB_1_INCLUDE_DIRS"] = os.path.join(
            self.dependencies["libusb"].package_folder, "include", "libusb-1.0")
        # Intl：上游 include_directories(${Intl_INCLUDE_DIRS})——CMake 内置
        # FindIntl 的 MODULE 探测在 OHOS sysroot 找到的是 musl 的内嵌 gettext
        # （无独立 libintl.h，声明不完整导致 nm_core.h 的 _() 内联报
        # int→char* 转换错）。显式指向 conan gettext 包。
        tc.cache_variables["Intl_INCLUDE_DIRS"] = os.path.join(
            self.dependencies["gettext"].package_folder, "include")
        # gettext/0.22.5.1 配方未声明 cpp_info.libs（Intl::Intl 是空
        # target），libintl 符号未定义。0001 补丁在 find_package(Intl)
        # 后给 Intl::Intl 注入 IMPORTED_LOCATION，路径由这两个变量提供。
        tc.cache_variables["NEMU_LIBINTL_PATH"] = os.path.join(
            self.dependencies["gettext"].package_folder, "lib", "libintl.so")
        tc.cache_variables["NEMU_LIBINTL_INC"] = os.path.join(
            self.dependencies["gettext"].package_folder, "include")
        jsonc_include = os.path.join(
            self.dependencies["json-c"].package_folder, "include", "json-c")
        tc.variables["CMAKE_C_FLAGS"] = "-D_GNU_SOURCE -I{}".format(jsonc_include)
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # find_package 优先 CONFIG：CMake 内置 FindIntl/FindLibXml2 等 MODULE
        # 探测在 OHOS sysroot 会命中 musl 内置 gettext（无 libintl.so 可链）
        # 导致 Intl_LIBRARIES 空、libintl_gettext 未定义。PREFER_CONFIG 让
        # find_package(Intl/LibXml2/...) 命中 CMakeDeps 生成的 CONFIG 文件。
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        self.run(f'cmake --build "{self.build_folder}" -- -j1')

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
