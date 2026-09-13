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

# OHOS 适配版 session.conf（依据 knowledge/doc/E461.md + 本机实测）：
#  - 监听：可写目录（CI TMPDIR，实测可 bind）→ /tmp（常规 Linux）→ linux 抽象命名
#    空间兜底（HMDFS 拒绝 file-socket bind，/tmp 为只读 erofs；分号分隔即回退链，实测有效）
#  - 认证：ANONYMOUS + allow_anonymous（EXTERNAL 需 UID 的 passwd 条目，OHOS 无 → NoReply）
#  - 不含 <standard_session_servicedirs/>（会触发 passwd 查找 → daemon 启动失败）
_OHOS_SESSION_CONF = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <keep_umask/>
  <listen>unix:tmpdir=/data/storage/el2/base/cache;unix:tmpdir=/tmp;unix:abstract=dbus-ohos-session</listen>
  <auth>ANONYMOUS</auth>
  <allow_anonymous/>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""


class DbusConan(ConanFile):
    name = "dbus"
    version = "1.14.10.1"
    description = "D-Bus message bus system — client library (libdbus-1)."
    license = "AFL-2.1 OR GPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/dbus/"
    url = "https://dbus.freedesktop.org/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"
    generators = "CMakeToolchain", "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dbus needs XML parsing (expat) — 对齐 gtk3 生态 2.8.2.1（gtk 图 override 同版本，
        # 避免图内重建；daemon 链接依赖其动态库）
        self.requires("expat/2.8.2.1")

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
        pass

    def build(self):
        cmake = CMake(self)
        variables = {
            # 禁用与消息总线守护进程无关的测试组件，仅构建客户端库 + 必要工具
            "DBUS_BUILD_TESTS": "OFF",
            # 1.14.10.1：需 dbus-run-session（tools/ 子目录，由本开关门控）；
            # 下游（dbus-python/libqtdbustest 等）以 find_program('dbus-run-session')
            # 探测，缺失则整体跳过其上游测试注册
            "DBUS_BUILD_TOOLS": "ON",
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
        # 1.14.10.1：dbus 源码 bus/CMakeLists 用 ${EXPAT_LIBRARIES} 链接 dbus-daemon。
        # CMakeDeps 的 Config 模式（expat::expat target）不会设置该变量 →
        # 显式传入 EXPAT_INCLUDE_DIR/EXPAT_LIBRARY/EXPAT_LIBRARIES 三个变量，
        # 使 find_package(EXPAT) 与 ${EXPAT_LIBRARIES} 展开均命中 conan 的 expat
        expat_dep = self.dependencies["expat"]
        expat_lib = os.path.join(expat_dep.package_folder, "lib", "libexpat.so")
        variables["EXPAT_INCLUDE_DIR"] = os.path.join(expat_dep.package_folder, "include")
        variables["EXPAT_LIBRARY"] = expat_lib
        variables["EXPAT_LIBRARIES"] = expat_lib
        cmake.configure(variables=variables)
        # 构建客户端库 dbus-1 与 dbus-daemon（1.14.10 曾跳过 daemon：OHOS 交叉编译下
        # 链接 expat 失败；1.14.10.1 修复链接（expat 2.8.2.1 动态库 + 显式链接顺序），
        # 供 gtk 测试环境 D-Bus session bus 使用，详见 notes.md）
        cmake.build(target="dbus-1")
        # 1.14.10.1：dbus-daemon（session bus 守护进程）与 dbus-run-session（工具，
        # 下游 find_program 探测用）——构建失败必须暴露，不得静默降级出包
        cmake.build(target="dbus-daemon")
        cmake.build(target="dbus-run-session")

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
        # dbus-daemon 与 dbus-run-session 可执行（1.14.10.1：供 session bus 及其
        # 下游 find_program 探测）。daemon 是本 PR 的交付承诺 → 缺失必须硬失败，
        # 不得静默降级出包（评审建议）
        pkg_bin = os.path.join(self.package_folder, "bin")
        daemon_candidates = (
            os.path.join(out, "bin", "dbus-daemon"),
            os.path.join(out, "bus", "dbus-daemon"),
        )
        run_session_candidates = (
            os.path.join(out, "bin", "dbus-run-session"),
            os.path.join(out, "tools", "dbus-run-session"),
        )
        daemon_src = next((p for p in daemon_candidates if os.path.isfile(p)), None)
        if daemon_src is None:
            raise ConanException(
                "dbus-daemon binary not found in build output "
                f"(candidates: {daemon_candidates}); refusing to publish "
                "a package claiming daemon support without it")
        os.makedirs(pkg_bin, exist_ok=True)
        shutil.copy2(daemon_src, os.path.join(pkg_bin, "dbus-daemon"))
        self.output.info(f"packaged dbus-daemon -> {pkg_bin}")
        run_session_src = next((p for p in run_session_candidates
                                if os.path.isfile(p)), None)
        if run_session_src is None:
            raise ConanException(
                "dbus-run-session binary not found in build output "
                f"(candidates: {run_session_candidates}); downstream "
                "find_program('dbus-run-session') would fail")
        shutil.copy2(run_session_src, os.path.join(pkg_bin, "dbus-run-session"))
        self.output.info(f"packaged dbus-run-session -> {pkg_bin}")
        # share/dbus-1/session.conf：dbus-daemon --session / dbus-run-session
        # （无 --config-file 时）读取的编译期固定路径。上游生成版在 OHOS 不可用
        # （listen unix:tmpdir=/tmp 遇只读 erofs、<auth>EXTERNAL 需 passwd 条目、
        # <standard_session_servicedirs/> 触发 passwd 查找）→ 写入适配版
        # （详见文件头 _OHOS_SESSION_CONF 注释与 knowledge/doc/E461.md）
        conf_dir = os.path.join(self.package_folder, "share", "dbus-1")
        os.makedirs(conf_dir, exist_ok=True)
        with open(os.path.join(conf_dir, "session.conf"), "w",
                  encoding="utf-8") as f:
            f.write(_OHOS_SESSION_CONF)
        self.output.info(f"packaged OHOS-adapted session.conf -> {conf_dir}")
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
