#!/usr/bin/env python3
"""Conan recipe for dbus 1.14.10 — CMake build (OHOS).

dbus provides libdbus-1 (D-Bus message bus client library), plus the
session bus daemon (dbus-daemon) and command-line tools (dbus-run-session,
dbus-send, dbus-monitor, ...). It is a prerequisite for Qt5DBus
(qt5-qtbase -dbus) and libngf-qt (NGF client), and enables real
D-Bus session-bus capability on OHOS (libdex test-dbus needs it).

Build strategy: use the upstream CMake build (patches 0001/0004 switch
the client library to STATIC to avoid OHOS HMDFS symlink issues). The
daemon and tools are built as normal executables and packaged into
bin/, together with the session config under share/dbus-1.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DbusConan(ConanFile):
    name = "dbus"
    version = "1.14.10.2"
    description = "D-Bus message bus system — client library, session bus daemon and tools."
    license = "AFL-2.1 OR GPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/dbus/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"
    generators = "CMakeToolchain", "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dbus needs XML parsing (expat)。r09：与 main 上 goblinrs 版 1.14.10.1
        # 合并收敛，expat 版本对齐 gtk3 生态 2.8.2.1（goblinrs 已入 main 的版本）
        self.requires("expat/2.8.2.1")
        # r07：引入 glib 依赖并开启 DBUS_WITH_GLIB，使 17 个 DBUS_WITH_GLIB 条件
        # 测试目标实例化（glib/2.88.3 为 ohpcd registry 既有发布，OHOS armv8 Release）
        self.requires("glib/2.88.3")

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
            # 构建会话总线守护进程与命令行工具（dbus-daemon/dbus-run-session 等），
            # 同时保留客户端静态库 dbus-1。
            # r04：上游测试最小纳入——启用测试构建（DBUS_BUILD_TESTS=ON 会同时
            # 打开 DBUS_ENABLE_EMBEDDED_TESTS/MODULAR_TESTS），按条件分支尝试实例化
            # 32 个 add_test_executable 目标并实际运行。
            # r07：开启 DBUS_WITH_GLIB=ON（引入 glib/2.88.3），使 17 个
            # DBUS_WITH_GLIB 条件测试目标实例化，冲刺 100% 通过。
            "DBUS_BUILD_TESTS": "ON",
            "DBUS_WITH_GLIB": "ON",
            "DBUS_ENABLE_DOXYGEN_DOCS": "OFF",
            "DBUS_ENABLE_XML_DOCS": "OFF",
            "DBUS_ENABLE_X11": "OFF",
            "DBUS_BUILD_X11": "OFF",
            "DBUS_ENABLE_SYSTEMD": "OFF",
            "DBUS_ENABLE_SELINUX": "OFF",
            "DBUS_ENABLE_APPARMOR": "OFF",
            "DBUS_ENABLE_MODULAR_TESTS": "ON",
            "DBUS_ENABLE_INSTALLED_TESTS": "OFF",
        }
        if str(self.settings.os) == "OHOS":
            # OHOS 环境无 X11/systemd，显式关闭
            variables["DBUS_ENABLE_X11"] = "OFF"
            variables["DBUS_BUILD_X11"] = "OFF"
        variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 无 CMake 平台文件（"System is unknown to cmake"），
        # 显式指定系统名走 UNIX 分支，避免误选 dbus-transport-win.c
        variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # 交叉编译时无法自动探测 session socket 目录，需显式指定
        variables["DBUS_SESSION_SOCKET_DIR"] = "/tmp"
        # dbus 顶层用标准 find_package(EXPAT)（FindEXPAT 模块，查系统路径），
        # 交叉编译时系统探测不到 expat.h → EXPAT_LIBRARIES 为空 →
        # dbus-daemon/dbus-daemon-launch-helper 链接 XML_* 符号失败。
        # 显式注入 conan 提供的 expat 头文件与库路径，使 FindEXPAT 命中。
        expat_pkg = self.dependencies["expat"].package_folder
        expat_lib = os.path.join(expat_pkg, "lib", "libexpat.so")
        if not os.path.isfile(expat_lib):
            # 兜底：若只有静态库则用它
            for cand in (os.path.join(expat_pkg, "lib", "libexpat.a"),):
                if os.path.isfile(cand):
                    expat_lib = cand
                    break
        variables["EXPAT_INCLUDE_DIR"] = os.path.join(expat_pkg, "include")
        variables["EXPAT_LIBRARY"] = expat_lib
        # bus/CMakeLists.txt 用 ${EXPAT_LIBRARIES} 链接 dbus-daemon 系列目标；
        # conan CMakeDeps 只定义 expat::expat 导入目标，不设置该复数变量。
        # 显式注入绝对路径库，使 dbus-daemon/dbus-daemon-launch-helper 链接生效。
        variables["EXPAT_LIBRARIES"] = expat_lib
        self.output.info(f"injecting EXPAT_INCLUDE_DIR={variables['EXPAT_INCLUDE_DIR']}")
        self.output.info(f"injecting EXPAT_LIBRARY={expat_lib}")
        self.output.info(f"injecting EXPAT_LIBRARIES={expat_lib}")
        # r07（DBUS_WITH_GLIB=ON）：dbus 顶层 find_package(GLIB2) 走标准
        # FindGLIB2 模块（查系统路径），交叉编译探测不到 glib；
        # conan CMakeDeps 只定义 glib2::glib 等组件目标，不设置 GLIB2_LIBRARIES。
        # 显式注入 include 与核心库路径，使 glib 条件测试目标（test-assertions/
        # test-corrupt/test-dbus-daemon 等 17 项）链接 g_* 符号成功。
        glib_pkg = self.dependencies["glib"].package_folder
        glib_libdir = os.path.join(glib_pkg, "lib")
        glib_libs = []
        # test-utils-glib.c 使用 g_dbus_connection_new_for_address_sync 等 GIO API，
        # 需连同 libgio-2.0 一起注入，否则 glib 条件测试目标链接 g_dbus_*/g_io_* 失败
        for name in ("libglib-2.0", "libgobject-2.0", "libgmodule-2.0", "libgio-2.0"):
            cand = os.path.join(glib_libdir, name + ".so")
            if not os.path.isfile(cand):
                cand = os.path.join(glib_libdir, name + ".a")
            if os.path.isfile(cand):
                glib_libs.append(cand)
        glib_libs_str = ";".join(glib_libs)
        variables["GLIB2_INCLUDE_DIRS"] = os.path.join(glib_pkg, "include", "glib-2.0")
        variables["GLIB2_LIBRARIES"] = glib_libs_str
        if glib_libs:
            variables["GLIB2_LIBRARY_DIRS"] = glib_libdir
        self.output.info(f"injecting GLIB2_INCLUDE_DIRS={variables['GLIB2_INCLUDE_DIRS']}")
        self.output.info(f"injecting GLIB2_LIBRARIES={glib_libs_str}")
        cmake.configure(variables=variables)
        # 全量构建：客户端库 + dbus-daemon + tools（dbus-run-session/dbus-send/
        # dbus-monitor/dbus-uuidgen/dbus-cleanup-sockets/dbus-launch 等）
        cmake.build()

    def package(self):
        # 手动复制产物（cmake.install() 会尝试安装未配置的 system 服务文件，
        # 手动复制更可控）
        b = self.build_folder
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

        # 静态库：dbus-1.a 与 dbus-internal.a（dbus/ 子目录）
        pkg_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(pkg_lib, exist_ok=True)
        for root, _dirs, files in os.walk(out):
            for f in files:
                if f.endswith(".a") and ("dbus" in root or "dbus" in f):
                    shutil.copy2(os.path.join(root, f), os.path.join(pkg_lib, f))
                    self.output.info(f"packed lib: {f}")

        # 可执行文件：dbus-daemon（bus/）、tools/ 下工具
        pkg_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(pkg_bin, exist_ok=True)
        tool_names = (
            "dbus-daemon", "dbus-run-session", "dbus-send", "dbus-monitor",
            "dbus-uuidgen", "dbus-cleanup-sockets", "dbus-launch",
            "dbus-test-tool", "dbus-update-activation-environment",
        )
        for root, _dirs, files in os.walk(out):
            for f in files:
                if f in tool_names and os.access(os.path.join(root, f), os.X_OK):
                    shutil.copy2(os.path.join(root, f), os.path.join(pkg_bin, f))
                    self.output.info(f"packed tool: {f}")

        # 头文件：源码在 build 根下 dbus/，生成的 dbus-arch-deps.h 在 build_folder/dbus/
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

        # 会话总线配置：session.conf（dbus-daemon --session 需要）
        conf = os.path.join(self.package_folder, "share", "dbus-1")
        os.makedirs(conf, exist_ok=True)
        found_conf = False
        for root, _dirs, files in os.walk(out):
            if "session.conf" in files:
                shutil.copy2(os.path.join(root, "session.conf"), os.path.join(conf, "session.conf"))
                found_conf = True
                self.output.info(f"packed session.conf from {root}")
                break
        if not found_conf:
            # 兜底：从源码生成目录复制
            for cand in (os.path.join(src_root, "bus"), os.path.join(b, "bus")):
                p = os.path.join(cand, "session.conf")
                if os.path.isfile(p):
                    shutil.copy2(p, os.path.join(conf, "session.conf"))
                    found_conf = True
                    self.output.info(f"packed session.conf (fallback) from {p}")
                    break
        if not found_conf:
            self.output.warning("session.conf not found — dbus-daemon --session may need --config-file")

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # dbus 头文件实际位于 include/dbus-1.0/dbus/（dbus-1.0 前缀），
        # 需同时暴露 include 与 include/dbus-1.0 供下游 #include <dbus/dbus.h>
        self.cpp_info.includedirs = ["include", "include/dbus-1.0"]
        self.cpp_info.libs = ["dbus-1"]
        self.cpp_info.set_property("cmake_file_name", "dbus")
        self.cpp_info.set_property("cmake_target_name", "dbus::dbus")
