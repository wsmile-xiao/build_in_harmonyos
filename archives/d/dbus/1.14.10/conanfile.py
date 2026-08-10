#!/usr/bin/env python3
"""Conan recipe for dbus 1.14.10 — CMake build (OHOS).

dbus provides libdbus-1 (D-Bus message bus client library). It is a
prerequisite for Qt5DBus (qt5-qtbase -dbus) and libngf-qt (NGF client).

Build strategy: use the upstream CMake build (patches 0001/0004 switch
to STATIC library) to avoid OHOS HMDFS symlink issues, matching the
recipe patches intended for this platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DbusConan(ConanFile):
    name = "dbus"
    version = "1.14.10"
    description = "D-Bus message bus system — client library (libdbus-1)."
    license = "AFL-2.1 OR GPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/dbus/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"
    generators = "CMakeToolchain", "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dbus needs XML parsing (expat)
        self.requires("expat/2.8.2")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dbus only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        # 显式传 url/sha256（conandata.yml 中的 tar_format 仅供校验，
        # get() 不识别该参数，不能通过 ** 展开传入）
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = tc.get("c")
        cxx = tc.get("cpp") or tc.get("cxx")
        if cc:
            self.run(f"echo CC={cc}", ignore_errors=True)  # no-op, compiler passed via profile

    def build(self):
        cmake = CMake(self)
        variables = {
            # 禁用与消息总线守护进程相关的组件，仅构建客户端库
            "DBUS_BUILD_TESTS": "OFF",
            "DBUS_BUILD_TOOLS": "OFF",
            "DBUS_ENABLE_DOXYGEN_DOCS": "OFF",
            "DBUS_ENABLE_XML_DOCS": "OFF",
            "DBUS_ENABLE_X11": "OFF",
            "DBUS_ENABLE_SYSTEMD": "OFF",
            "DBUS_ENABLE_SELINUX": "OFF",
            "DBUS_ENABLE_APPARMOR": "OFF",
            "DBUS_ENABLE_EMBEDDED_TESTS": "OFF",
            "DBUS_ENABLE_MODULAR_TESTS": "OFF",
            "DBUS_ENABLE_INSTALLED_TESTS": "OFF",
        }
        if str(self.settings.os) == "OHOS":
            # OHOS 环境无 X11/systemd，显式关闭
            variables["DBUS_ENABLE_X11"] = "OFF"
        variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 无 CMake 平台文件（"System is unknown to cmake"），
        # 显式指定系统名走 UNIX 分支，避免误选 dbus-transport-win.c
        variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # 交叉编译时无法自动探测 session socket 目录，需显式指定
        variables["DBUS_SESSION_SOCKET_DIR"] = "/tmp"
        cmake.configure(variables=variables)
        # 仅构建客户端库 dbus-1（跳过 dbus-daemon/tools/doc：
        # daemon 在 OHOS 交叉编译下链接 expat 失败，且本配方只需客户端库）
        cmake.build(target="dbus-1")

    def package(self):
        # 仅打包客户端库产物（cmake.install() 会尝试安装未构建的
        # dbus-daemon 导致失败，改为手动复制）
        import shutil
        b = self.build_folder
        # CMake 构建输出目录（cmake_layout：build/Release）
        out = None
        for candidate in (
            os.path.join(b, "build", "Release"),
            os.path.join(b, "Release"),
            b,
        ):
            if os.path.isdir(candidate):
                out = candidate
                break
        self.output.info(f"build output dir: {out}")
        if out is None:
            raise ConanException("unable to locate cmake build output dir")
        # 静态库
        lib_dir = os.path.join(out, "lib")
        if os.path.isdir(lib_dir):
            pkg_lib = os.path.join(self.package_folder, "lib")
            os.makedirs(pkg_lib, exist_ok=True)
            for f in os.listdir(lib_dir):
                if f.endswith(".a"):
                    shutil.copy2(os.path.join(lib_dir, f),
                                 os.path.join(pkg_lib, f))
        # 头文件：源码在 build 根下 dbus/（如 .../b/dbus），
        # 生成的 dbus-arch-deps.h 在 build_folder/dbus/
        inc = os.path.join(self.package_folder, "include", "dbus-1.0", "dbus")
        os.makedirs(inc, exist_ok=True)
        src_root = os.path.dirname(os.path.dirname(self.build_folder))
        for hdir in (
            os.path.join(src_root, "dbus"),          # 源码公共头
            os.path.join(self.build_folder, "dbus"), # 生成头
        ):
            if os.path.isdir(hdir):
                for f in os.listdir(hdir):
                    if f.endswith(".h"):
                        shutil.copy2(os.path.join(hdir, f), os.path.join(inc, f))

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        # dbus 头文件实际位于 include/dbus-1.0/dbus/（dbus-1.0 前缀），
        # 需同时暴露 include 与 include/dbus-1.0 供下游 #include <dbus/dbus.h>
        self.cpp_info.includedirs = ["include", "include/dbus-1.0"]
        self.cpp_info.libs = ["dbus-1"]
        self.cpp_info.set_property("cmake_file_name", "dbus")
        self.cpp_info.set_property("cmake_target_name", "dbus::dbus")
