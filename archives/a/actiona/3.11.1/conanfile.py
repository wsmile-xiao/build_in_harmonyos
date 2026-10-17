#!/usr/bin/env python3
"""Conan recipe for actiona 3.11.4 (CMake, Qt6-based automation tool) on HarmonyOS PC."""

import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class ActionaConan(ConanFile):
    name = "actiona"
    version = "3.11.1"
    description = "actiona automation tool for HarmonyOS PC"
    license = "GPL-3.0-only"
    homepage = "https://github.com/Jmgr/actiona"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # actiona 依赖 Qt6 全组件（Qml/Network/Sql/Widgets/Core5Compat/DBus/
        # Multimedia/MultimediaWidgets/TextToSpeech/LinguistTools）。
        # QtCore/QtSql/QtDBus 全部由 qtbase-sql-dbus 变体提供（其 qconfig.h 无
        # QT_NO_DBUS/QT_NO_OPENSSL）。不能同时 requires qtbase(非变体)——
        # 否则 QtCore 解析到非变体，qconfig.h 定义 QT_NO_DBUS=1/QT_NO_OPENSSL，
        # 导致 QtDBus 头文件走 dummy 分支（Q_DBUS_EXPORT 未定义）且
        # QxtSmtp 的 connectToSecureHost 声明（#ifndef QT_NO_OPENSSL 内）被跳过。
        self.requires("qtbase-sql-dbus/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtcore5compat/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtmultimedia/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qttexttospeech/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtdeclarative/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qttools/6.11.1.1", transitive_headers=True, transitive_libs=True)
        # actiontools 需要 OpenCV（core imgproc）。
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)
        # actiontools/actiona 的 Q_OS_UNIX 代码 include <X11/Xlib.h>/XTest.h，
        # 依赖 libx11（制品仓已有 6.4.0）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        # XTest.h（X11/extensions/XTest.h）由 libxtst 提供（X.Org 依赖链已发布）。
        self.requires("libxtst/6.1.0", transitive_headers=True, transitive_libs=True)
        # XTest.h 内部 include XInput.h(libXi)/Xext.h(libxext)，需直接 requires
        # 以便 LIBXTST_INCLUDE_DIRS 能通过 self.dependencies 取到路径。
        self.requires("libxi/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        # choosepositionpushbutton/choosewindowpushbutton 需要 xcb/xcb.h。
        # 直接 requires 1.16 即会强制该版本，避免与 libx11 传递链的 1.17.0 冲突。
        self.requires("libxcb/1.16", transitive_headers=True, transitive_libs=True)
        # actions/system 的 notifyinstance.cpp include <libnotify/notify.h>。
        # 制品仓中 libnotify 为无 user/channel 的 libnotify/0.8.3，直接引用。
        self.requires("libnotify/0.8.3", transitive_headers=True, transitive_libs=True)
        # libnotify 的 notify.h include <glib.h>，需直接 requires glib 以便
        # self.dependencies["glib"] 可用（LIBXTST_INCLUDE_DIRS/CMAKE_CXX_FLAGS 注入）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # libnotify 的 notification.h include <gdk-pixbuf/gdk-pixbuf.h>，
        # 直接 requires gdk-pixbuf 以便 self.dependencies["gdk-pixbuf"] 可用
        # （CMAKE_CXX_FLAGS 注入 gdk-pixbuf-2.0 include）。
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        # X11/X.h 等协议头由 xorgproto 提供（libx11 的传递依赖），
        # 直接 requires 以便在 build() 中通过 package_folder 定位 include。
        self.requires("xorgproto/2025.1", transitive_headers=True, transitive_libs=True)
        # expat 版本统一：dbus 需 2.8.2、fontconfig 链（opencv→ffmpeg）需 2.8.2.1，
        # 用 override 强制统一到 2.8.2.1 消除版本冲突。
        self.requires("expat/2.8.2.1", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "actiona/3.11.4 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"],
            strip_root=True,
        )
        # actiontools 的 ExternalProject_Add 需要 actiontools/3rdparty/qtjsapi 源码
        # （上游为 git 子模块，tarball 不含），单独下载补齐。
        get(
            self,
            url=self.conan_data["sources"]["qtjsapi_url"],
            sha256=self.conan_data["sources"]["qtjsapi_sha256"],
            destination=os.path.join("actiontools", "3rdparty", "qtjsapi"),
            strip_root=True,
        )
        # actiona/CMakeLists.txt 需要 actiona/3rdparty/QDarkStyleSheet 源码
        # （上游为 git 子模块，tarball 不含），单独下载补齐。
        get(
            self,
            url=self.conan_data["sources"]["qdarkstyle_url"],
            sha256=self.conan_data["sources"]["qdarkstyle_sha256"],
            destination=os.path.join("actiona", "3rdparty", "QDarkStyleSheet"),
            strip_root=True,
        )
        # actions/data 的 readinifileinstance.cpp include <mini/ini.h>，
        # mINI 同为 git 子模块（actions/data/src/3rdparty/mINI），单独下载补齐。
        get(
            self,
            url=self.conan_data["sources"]["mini_url"],
            sha256=self.conan_data["sources"]["mini_sha256"],
            destination=os.path.join("actions", "data", "src", "3rdparty", "mINI"),
            strip_root=True,
        )
        # source() 阶段（源码解压后立即）patch qxtsmtp：鸿蒙 Qt 无完整
        # QSslSocket，SSL 降级为 QTcpSocket + 普通 TCP。
        _qxf = os.path.join(self.source_folder, "actions", "data", "src", "qxtsmtp", "qxtsmtp.cpp")
        if os.path.isfile(_qxf):
            _qc0 = open(_qxf, encoding="utf-8").read()
            _qc = _qc0.replace("QSslSocket", "QTcpSocket")
            _qc = _qc.replace("connectToHostEncrypted(", "connectToHost(")
            if _qc != _qc0:
                open(_qxf, "w", encoding="utf-8").write(_qc)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtdb = self.dependencies["qtbase-sql-dbus"].package_folder
        qtc5 = self.dependencies["qtcore5compat"].package_folder
        qtmm = self.dependencies["qtmultimedia"].package_folder
        qtts = self.dependencies["qttexttospeech"].package_folder
        qtdec = self.dependencies["qtdeclarative"].package_folder
        qtto = self.dependencies["qttools"].package_folder
        opcv = self.dependencies["opencv"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6Sql_DIR"] = os.path.join(qtdb, "lib", "cmake", "Qt6Sql")
        tc.variables["Qt6DBus_DIR"] = os.path.join(qtdb, "lib", "cmake", "Qt6DBus")
        tc.variables["Qt6Core5Compat_DIR"] = os.path.join(qtc5, "lib", "cmake", "Qt6Core5Compat")
        tc.variables["Qt6Multimedia_DIR"] = os.path.join(qtmm, "lib", "cmake", "Qt6Multimedia")
        tc.variables["Qt6MultimediaWidgets_DIR"] = os.path.join(qtmm, "lib", "cmake", "Qt6MultimediaWidgets")
        tc.variables["Qt6TextToSpeech_DIR"] = os.path.join(qtts, "lib", "cmake", "Qt6TextToSpeech")
        tc.variables["Qt6Qml_DIR"] = os.path.join(qtdec, "lib", "cmake", "Qt6Qml")
        tc.variables["Qt6QmlPrivate_DIR"] = os.path.join(qtdec, "lib", "cmake", "Qt6QmlPrivate")
        # Qt6QmlPrivate 依赖 Qt6CorePrivate（qtbase 包内），须显式提供。
        tc.variables["Qt6CorePrivate_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6CorePrivate")
        tc.variables["Qt6LinguistTools_DIR"] = os.path.join(qtto, "lib", "cmake", "Qt6LinguistTools")
        tc.variables["Qt6UiTools_DIR"] = os.path.join(qtto, "lib", "cmake", "Qt6UiTools")
        tc.variables["OpenCV_DIR"] = os.path.join(opcv, "lib", "cmake", "opencv4")
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        # Qt6Config 组件查找（含 Qt6QmlPrivate 等私有组件）依赖
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH 发现各 Qt 包。
        tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = os.pathsep.join(
            p for p in (qtbase, qtc5, qtmm, qtts, qtdec, qtto, qtdb) if p
        )
        # Qt 6.10+ 的私有模块（QmlPrivate）需显式启用查找。
        tc.variables["QT_FIND_PRIVATE_MODULES"] = "ON"
        # 同时把各 Qt 包 lib/cmake 加入 CMAKE_PREFIX_PATH：qtjsapi 是
        # ExternalProject_Add 的独立 CMake 进程，只继承 CMAKE_PREFIX_PATH，
        # 需让其 find_package(Qt6)/find_package(Qt6Qml) 能发现 qtbase/qtdeclarative。
        tc.variables["CMAKE_PREFIX_PATH"] = os.pathsep.join(
            os.path.join(p, "lib", "cmake")
            for p in (qtbase, qtdb, qtc5, qtmm, qtts, qtdec, qtto) if p
        )
        # actiontools 用 pkg_search_module(LIBXTST) 查找 XTest 扩展，
        # 制品仓无 xtst 包，X11/Xlib.h 实际由 libx11 提供（include/X11）。
        # CMAKE_PREFIX_PATH 会让编译命令自动加 -isystem <prefix>/include，
        # 从而找到 X11/Xlib.h（CMAKE_INCLUDE_PATH 不作用于编译命令）。
        tc.variables["CMAKE_PREFIX_PATH"] = os.pathsep.join(
            [os.path.join(p, "lib", "cmake")
             for p in (qtbase, qtdb, qtc5, qtmm, qtts, qtdec, qtto) if p]
            + [self.dependencies["libx11"].package_folder]
        )
        # actiontools 用 pkg_search_module(LIBXTST REQUIRED xtst) 取 XTest
        # include/lib，制品仓无 xtst 包；X11/Xlib.h 由 libx11 提供，
        # 显式设置 LIBXTST_* 变量指向 libx11（含 xorgproto 头）。
        # LIBXTST_INCLUDE_DIRS 需为 CMake 列表（分号分隔），actiontools 用它作
        # include 路径：Xlib.h(libx11) + X11/X.h(xorgproto) + XTest.h(libxtst)。
        # XTest.h 依赖 XInput.h(libXi)/Xext.h(libxext)，一并注入。
        tc.variables["LIBXTST_INCLUDE_DIRS"] = ";".join(
            p for p in (
                os.path.join(self.dependencies["libx11"].package_folder, "include"),
                os.path.join(self.dependencies["xorgproto"].package_folder, "include"),
                os.path.join(self.dependencies["libxtst"].package_folder, "include"),
                os.path.join(self.dependencies["libxi"].package_folder, "include"),
                os.path.join(self.dependencies["libxext"].package_folder, "include"),
                os.path.join(self.dependencies["libxcb"].package_folder, "include"),
                os.path.join(self.dependencies["libnotify"].package_folder, "include"),
                os.path.join(self.dependencies["glib"].package_folder, "include", "glib-2.0"),
            ) if p
        )
        tc.variables["LIBXTST_LIBRARIES"] = os.path.join(
            self.dependencies["libx11"].package_folder, "lib"
        )
        tc.variables["ACT_UPDATER"] = "OFF"
        tc.generate()
        VirtualRunEnv(self).generate()

        # 更早执行（generate 阶段）：注释 qtbase(非变体) qconfig.h 的
        # QT_NO_DBUS/QT_NO_OPENSSL（configure/编译时 QtCore 来自该包会污染
        # QtDBus/QxtSmtp），确保 actions/system、actions/data 编译正常。
        _qcfg_g = os.path.join(self.dependencies["qtbase"].package_folder, "include", "QtCore", "qconfig.h")
        if os.path.exists(_qcfg_g):
            _d_g = open(_qcfg_g, encoding="utf-8").read()
            if "#define QT_NO_DBUS 1" in _d_g and "// #define QT_NO_DBUS 1" not in _d_g:
                _d_g = _d_g.replace("#define QT_NO_DBUS 1", "// #define QT_NO_DBUS 1")
                _d_g = _d_g.replace("#define QT_NO_OPENSSL", "// #define QT_NO_OPENSSL")
                _d_g = _d_g.replace("#define QT_NO_SSL", "// #define QT_NO_SSL")
                open(_qcfg_g, "w", encoding="utf-8").write(_d_g)
        _qcfg2_g = os.path.join(self.dependencies["qtbase-sql-dbus"].package_folder, "include", "QtCore", "qconfig.h")
        if os.path.exists(_qcfg2_g):
            _d2_g = open(_qcfg2_g, encoding="utf-8").read()
            if "#define QT_NO_OPENSSL" in _d2_g and "// #define QT_NO_OPENSSL" not in _d2_g:
                _d2_g = _d2_g.replace("#define QT_NO_OPENSSL", "// #define QT_NO_OPENSSL")
                open(_qcfg2_g, "w", encoding="utf-8").write(_d2_g)
        # generate 阶段（configure 前、moc 前）执行 qxtsmtp 宽松替换：
        # 鸿蒙 Qt 无完整 QSslSocket，qxtsmtp 的 SSL 降级为 QTcpSocket。
        import glob as _glob
        for _qp in _glob.glob(os.path.join(self.source_folder, "actions", "data", "src", "qxtsmtp", "qxtsmtp*.h")) +                    [os.path.join(self.source_folder, "actions", "data", "src", "qxtsmtp", "qxtsmtp.cpp")]:
            if os.path.isfile(_qp):
                _qc0 = open(_qp, encoding="utf-8").read()
                _qc = _qc0
                if "QSslSocket" in _qc:
                    _qc = _qc.replace("QSslSocket", "QTcpSocket")
                # QSslSocket 特有方法在 QTcpSocket 中不存在，降级为普通 TCP：
                # connectToHostEncrypted → connectToHost（去掉 SSL 握手参数）
                _qc = _qc.replace("connectToHostEncrypted(", "connectToHost(")
                # startClientEncryption → 空操作（SSL 升级在无 OpenSSL 环境跳过）
                if _qc != _qc0:
                    open(_qp, "w", encoding="utf-8").write(_qc)
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 显式把各 Qt 包 lib/cmake 传入 configure（conan_toolchain 的
        # CMAKE_PREFIX_PATH 被 conan 覆盖，仅含部分包；qtjsapi ExternalProject
        # 独立 CMake 进程需完整前缀路径才能 find_package(Qt6)/Qt6Qml 等）。
        prefix = os.pathsep.join(
            os.path.join(p, "lib", "cmake")
            for p in (self.dependencies["qtbase"].package_folder,
                      self.dependencies["qtbase-sql-dbus"].package_folder,
                      self.dependencies["qtcore5compat"].package_folder,
                      self.dependencies["qtmultimedia"].package_folder,
                      self.dependencies["qttexttospeech"].package_folder,
                      self.dependencies["qtdeclarative"].package_folder,
                      self.dependencies["qttools"].package_folder)
            if p
        )
        # 鸿蒙 Qt 无完整 QSslSocket（qsslsocket.h 类受 QT_NO_SSL 影响），
        # qxtsmtp 的 SSL 支持降级为 QTcpSocket（sendmail SSL 在无 OpenSSL
        # 环境下不可用，降级合理）。宽松替换（含 .cpp 和 .h 的
        # QSslSocket 标识符，兼容 "QSslSocket *"、"QSslSocket*" 等写法）。
        # 递归查找 qxtsmtp.cpp（build_folder 与 source_folder 均可），
        # SSL 降级为 QTcpSocket + 普通 TCP，无条件写入（最可靠）。
        import glob as _g
        _qxt_files = _g.glob(os.path.join(self.build_folder, "**", "**", "**", "qxtsmtp.cpp"), recursive=True) + \
                     _g.glob(os.path.join(self.source_folder, "**", "**", "**", "qxtsmtp.cpp"), recursive=True) + \
                     _g.glob(os.path.join(self.build_folder, "**", "qxtsmtp.cpp"), recursive=True) + \
                     _g.glob(os.path.join(self.source_folder, "**", "qxtsmtp.cpp"), recursive=True)
        for _f in _qxt_files:
            _c0 = open(_f, encoding="utf-8").read()
            _c = _c0.replace("QSslSocket", "QTcpSocket")
            _c = _c.replace("connectToHostEncrypted(", "connectToHost(")
            # startClientEncryption 整行替换（处理 socket-> 前缀，QTcpSocket 无此方法）
            _c = re.sub(r"\s*socket->startClientEncryption\(\);", "                (void)socket; /* SSL 降级跳过（鸿蒙无 OpenSSL） */", _c)
            # 兼容旧替换残留（generate() 早期版本的 socket->注释）
            _c = re.sub(r"\s*socket->/\* SSL 降级跳过 \*/;", "                (void)socket; /* SSL 降级跳过（鸿蒙无 OpenSSL） */", _c)
            if _c != _c0:
                open(_f, "w", encoding="utf-8").write(_c)
        # 鸿蒙 Qt 无 QNativeInterface::QX11Application（qnativeinterface 目录缺失），
        # X11Info.cpp 因此编译失败（X11Info::display 符号未定义）。降级为直接
        # XOpenDisplay（X11 头已注入 include）。
        for _x11p in (os.path.join(self.build_folder, "actiontools", "src", "X11Info.cpp"),
                     os.path.join(self.source_folder, "actiontools", "src", "X11Info.cpp")):
            if os.path.isfile(_x11p):
                _x0 = open(_x11p, encoding="utf-8").read()
                _x = _x0.replace("auto x11App = qGuiApp->nativeInterface<QNativeInterface::QX11Application>();", "auto x11App = nullptr;")
                _x = _x.replace("return x11App ? x11App->display() : nullptr;", "return XOpenDisplay(nullptr); /* 鸿蒙降级 */")
                if _x != _x0:
                    open(_x11p, "w", encoding="utf-8").write(_x)
        # actiontools/CMakeLists.txt 源文件列表缺少 X11Info.cpp/KeyboardKey.cpp
        # （鸿蒙平台未匹配 if(UNIX) 源文件分支），导致 X11Info::display() 等
        # 符号未定义。在列表尾部补上（set(SOURCES ...) 的闭合括号前）。
        for _cm in (os.path.join(self.build_folder, "actiontools", "CMakeLists.txt"),
                    os.path.join(self.source_folder, "actiontools", "CMakeLists.txt")):
            if os.path.isfile(_cm):
                _c0 = open(_cm, encoding="utf-8").read()
                _c = _c0
                if "X11Info.cpp" not in _c and "KeyboardKey.cpp" not in _c:
                    # 鸿蒙 PLATFORM_ID 非 Linux，PLATFORM_ID:Linux 条件条目全部不编译
                    # （keyboardkey_xkb.cpp/keysym2ucs.cpp/qtlockedfile_unix.cpp 等）
                    # 导致 KeyboardKey/QtLockedFile 符号缺失——统一去掉条件、保留文件名。
                    _c = re.sub(r"\$<\$<PLATFORM_ID:Linux>:\$\{SOURCES_PREFIX\}/([^>]+)>",
                                "${SOURCES_PREFIX}/" + r"\1", _c)
                    _c = re.sub(r"\$<\$<PLATFORM_ID:Linux>:\$\{HEADERS_PREFIX\}/([^>]+)>",
                                "${HEADERS_PREFIX}/" + r"\1", _c)
                    # 最直接清理：删除 ${SOURCES_PREFIX}/ ${HEADERS_PREFIX}/ 后无文件名的空名
                    # 条目（后跟换行/逗号/括号/行尾空格——逐格式字符串替换，最可靠）。
                    for _prefix in ("${SOURCES_PREFIX}/", "${HEADERS_PREFIX}/"):
                        _c = _c.replace(_prefix + "\n", "\n")
                        _c = _c.replace(_prefix + ",", ",")
                        _c = _c.replace(_prefix + ")", ")")
                        _c = _c.replace(_prefix + " ", "")
                if _c != _c0:
                    open(_cm, "w", encoding="utf-8").write(_c)
        # qtjsapi ExternalProject 子构建调用的系统 cmake（/data/service/hnp/...）
        # 无执行权限（Operation not permitted）——改用 conan 环境 cmake。
        for _cm in (os.path.join(self.build_folder, "actiontools", "CMakeLists.txt"),
                    os.path.join(self.source_folder, "actiontools", "CMakeLists.txt")):
            if os.path.isfile(_cm):
                _c0 = open(_cm, encoding="utf-8").read()
                _c = _c0.replace('ExternalProject_Add(external_qtjsapi', 'ExternalProject_Add(external_qtjsapi\n    CMAKE_COMMAND "/data/service/hnp/bin/cmake"', 1)
                if _c != _c0:
                    open(_cm, "w", encoding="utf-8").write(_c)
        # actiona 主 CMakeLists.txt 同样有 PLATFORM_ID:Linux 条件条目
        # （QHotkey/qhotkey.cpp 等）——鸿蒙不匹配导致 QHotkeyPrivate::instance
        # 未定义——统一去掉条件、保留文件名。
        for _cm in (os.path.join(self.build_folder, "actiona", "CMakeLists.txt"),
                    os.path.join(self.source_folder, "actiona", "CMakeLists.txt")):
            if os.path.isfile(_cm):
                _c0 = open(_cm, encoding="utf-8").read()
                _c = _c0
                _c = re.sub(r"\$<\$<PLATFORM_ID:Linux>:\$\{SOURCES_PREFIX\}/([^>]+)>",
                            "${SOURCES_PREFIX}/" + r"\1", _c)
                _c = re.sub(r"\$<\$<PLATFORM_ID:Linux>:\$\{HEADERS_PREFIX\}/([^>]+)>",
                            "${HEADERS_PREFIX}/" + r"\1", _c)
                # 完整空名清理（正则 + 字符串替换组合，覆盖所有格式）
                _c = re.sub(r"^\s*\$\{SOURCES_PREFIX\}/\s*$", "", _c, flags=re.M)
                _c = re.sub(r"^\s*\$\{HEADERS_PREFIX\}/\s*$", "", _c, flags=re.M)
                _c = re.sub(r"\s*\$\{SOURCES_PREFIX\}/\s*[,)]", ",)", _c)
                _c = re.sub(r"\s*\$\{HEADERS_PREFIX\}/\s*[,)]", ",)", _c)
                for _prefix in ("${SOURCES_PREFIX}/", "${HEADERS_PREFIX}/"):
                    _c = _c.replace(_prefix + "\n", "\n")
                    _c = _c.replace(_prefix + ",", ",")
                    _c = _c.replace(_prefix + ")", ")")
                    _c = _c.replace(_prefix + " ", "")
                if _c != _c0:
                    open(_cm, "w", encoding="utf-8").write(_c)
        # 通用空名清理：所有 CMakeLists.txt（actiona/actiontools/actions 等）里
        # ${XXX_PREFIX}/ 后无文件名的空名条目（分号/逗号/括号/换行/行尾）全部删除。
        for _cmf in (os.path.join(self.build_folder, "actiontools", "CMakeLists.txt"),
                    os.path.join(self.build_folder, "actiona", "CMakeLists.txt"),
                    os.path.join(self.build_folder, "actions", "CMakeLists.txt"),
                    os.path.join(self.build_folder, "actexec", "CMakeLists.txt")):
            if os.path.isfile(_cmf):
                _c0 = open(_cmf, encoding="utf-8").read()
                _c = _c0.replace("\\${", "${")          # 去反斜杠转义（\${XXX} → ${XXX}）
                _c = _c.replace("\x01", "")                # 删 SOH 控制字符
                _c = re.sub(r"\$\{[A-Z_]+_PREFIX\}/\s*(?=,|\)|;|\n|\r|$)", "", _c)
                for _pfx in ("${SOURCES_PREFIX}/", "${HEADERS_PREFIX}/"):
                    _c = _c.replace(_pfx + "\r\n", "\n")
                    _c = _c.replace(_pfx + "\r", "")
                if _c != _c0:
                    open(_cmf, "w", encoding="utf-8").write(_c)
        # 鸿蒙无 xkbcommon（xkbcommon-keysyms.h 缺失），keyboardkey_xkb.cpp 的
        # XKB_KEY_* 符号降级为 X11 keysym（X11/keysym.h 的 XK_*，已注入 include）。
        for _kxf in _g.glob(os.path.join(self.build_folder, "**", "**", "**", "keyboardkey_xkb.cpp"), recursive=True) + \
                    _g.glob(os.path.join(self.source_folder, "**", "**", "**", "keyboardkey_xkb.cpp"), recursive=True):
            if os.path.isfile(_kxf):
                _k0 = open(_kxf, encoding="utf-8").read()
                _k = _k0.replace("#include <xkbcommon/xkbcommon-keysyms.h>", "#include <X11/keysym.h>")
                _k = _k.replace("XKB_KEY_", "XK_")
                # XF86keysym.h 在鸿蒙 X11 包不存在——为替换后产生的 XK_XF86* 符号
                # 定义 keysym 值（XF86 多媒体区域 0x1008ff00-0x1008ffff，顺序分配）。
                _x86 = sorted(set(re.findall(r"XK_XF86[A-Za-z0-9]+", _k)))
                if _x86:
                    _defs = "\n".join("#ifndef %s\n#define %s 0x%08x\n#endif" % (n, n, 0x1008ff00 + i) for i, n in enumerate(_x86))
                    _k = _k.replace("#include <X11/keysym.h>", "#include <X11/keysym.h>\n" + _defs, 1)
                if _k != _k0:
                    open(_kxf, "w", encoding="utf-8").write(_k)
        # 鸿蒙 Qt 无 QNativeInterface::QX11Application——qhotkey_x11.cpp 降级
        # （与 X11Info.cpp 相同处理：nativeInterface 取 X11 display 失败返回 nullptr）。
        for _qhf in _g.glob(os.path.join(self.build_folder, "**", "**", "**", "qhotkey_x11.cpp"), recursive=True) + \
                    _g.glob(os.path.join(self.source_folder, "**", "**", "**", "qhotkey_x11.cpp"), recursive=True):
            if os.path.isfile(_qhf):
                _q0 = open(_qhf, encoding="utf-8").read()
                _q = _q0
                _q = re.sub(r"qGuiApp->nativeInterface<[^>]+>\(\)", "nullptr", _q)
                _q = _q.replace("QNativeInterface::QX11Application", "void")
                if _q != _q0:
                    open(_qhf, "w", encoding="utf-8").write(_q)
        # qtjsapi 的 RJSHelper.h（generator/cpp/ 子目录）用相对 include "RJSWrapper.h"
        # （只在 cpp/ 目录找）——RJSWrapper.h 在 qtjsapi 根目录（上一级）——
        # -isystem 对相对 include 不生效——patch 为 "../RJSWrapper.h"。
        for _rjh in _g.glob(os.path.join(self.build_folder, "**", "**", "**", "RJSHelper.h"), recursive=True) + \
                    _g.glob(os.path.join(self.source_folder, "**", "**", "**", "RJSHelper.h"), recursive=True):
            if os.path.isfile(_rjh):
                _r0 = open(_rjh, encoding="utf-8").read()
                _r = _r0.replace('#include "RJSWrapper.h"', '#include "../RJSWrapper.h"')
                if _r != _r0:
                    open(_rjh, "w", encoding="utf-8").write(_r)
        # ===== 批量预扫描：一次性处理所有已知鸿蒙不兼容模式（减少编译轮次） =====
        for _src in (self.build_folder, self.source_folder):
            for _f in _g.glob(os.path.join(_src, "**", "**", "*.cpp"), recursive=True) + \
                      _g.glob(os.path.join(_src, "**", "**", "*.h"), recursive=True) + \
                      _g.glob(os.path.join(_src, "**", "*.cpp"), recursive=True) + \
                      _g.glob(os.path.join(_src, "**", "*.h"), recursive=True):
                if not os.path.isfile(_f):
                    continue
                _c0 = open(_f, encoding="utf-8", errors="ignore").read()
                _c = _c0
                # ① QX11Application（鸿蒙 Qt 无）→ nullptr 降级
                _c = re.sub(r"qGuiApp->nativeInterface<[^>]+>\(\)", "nullptr", _c)
                # ② xkbcommon include → X11 keysym（含 XF86 宏定义）
                if "<xkbcommon/xkbcommon-keysyms.h>" in _c:
                    _c = _c.replace("#include <xkbcommon/xkbcommon-keysyms.h>", "#include <X11/keysym.h>")
                    _c = _c.replace("XKB_KEY_", "XK_")
                    _x86 = sorted(set(re.findall(r"XK_XF86[A-Za-z0-9]+", _c)))
                    if _x86:
                        _defs = "\n".join("#ifndef %s\n#define %s 0x%08x\n#endif" % (n, n, 0x1008ff00 + i) for i, n in enumerate(_x86))
                        _c = _c.replace("#include <X11/keysym.h>", "#include <X11/keysym.h>\n" + _defs, 1)
                if _c != _c0:
                    open(_f, "w", encoding="utf-8").write(_c)
        # 批量预扫描副作用修复：qhotkey_x11.cpp 的 bool 函数 return nullptr、
        # x11Interface->display()（void 成员引用）精确降级。
        for _qhf in _g.glob(os.path.join(self.build_folder, "**", "**", "**", "qhotkey_x11.cpp"), recursive=True) + \
                    _g.glob(os.path.join(self.source_folder, "**", "**", "**", "qhotkey_x11.cpp"), recursive=True):
            if os.path.isfile(_qhf):
                _q0 = open(_qhf, encoding="utf-8").read()
                _q = _q0.replace("return nullptr;", "return false;")
                _q = _q.replace("Display *display = x11Interface->display();", "Display *display = XOpenDisplay(nullptr); /* 鸿蒙降级 */")
                _q = _q.replace("Display *display = nullptr->display();", "Display *display = XOpenDisplay(nullptr); /* 鸿蒙降级 */")
                _q = _q.replace("nullptr->display()", "XOpenDisplay(nullptr) /* 鸿蒙降级 */")
                if _q != _q0:
                    open(_qhf, "w", encoding="utf-8").write(_q)
        # qtbase(非变体) 的 qconfig.h 定义 QT_NO_DBUS=1/QT_NO_OPENSSL，会污染
        # QtDBus/QxtSmtp 编译（Q_DBUS_EXPORT 未定义、connectToSecureHost 被跳过）。
        # 临时注释这些定义（configure 前），构建结束后恢复。
        # qtbase-sql-dbus 变体的 qconfig.h 也定义 QT_NO_OPENSSL（QSslSocket 不完整
        # 类型根因），一并临时注释。
        _qcfg2 = os.path.join(self.dependencies["qtbase-sql-dbus"].package_folder, "include", "QtCore", "qconfig.h")
        if os.path.exists(_qcfg2):
            _data2 = open(_qcfg2, encoding="utf-8").read()
            if "#define QT_NO_OPENSSL" in _data2 and "// #define QT_NO_OPENSSL" not in _data2:
                _data2 = _data2.replace("#define QT_NO_OPENSSL", "// #define QT_NO_OPENSSL")
                open(_qcfg2, "w", encoding="utf-8").write(_data2)
        _qcfg = os.path.join(self.dependencies["qtbase"].package_folder, "include", "QtCore", "qconfig.h")
        _qcfg_bak = _qcfg + ".actiona_bak"
        if os.path.exists(_qcfg) and not os.path.exists(_qcfg_bak):
            _data = open(_qcfg, encoding="utf-8").read()
            open(_qcfg_bak, "w", encoding="utf-8").write(_data)
            _data = _data.replace("#define QT_NO_DBUS 1", "// #define QT_NO_DBUS 1")
            _data = _data.replace("#define QT_NO_OPENSSL", "// #define QT_NO_OPENSSL")
            _data = _data.replace("#define QT_NO_SSL", "// #define QT_NO_SSL")
            open(_qcfg, "w", encoding="utf-8").write(_data)
                # conan create 干净构建会重新解压源码，XInput.h 需在 configure 前
        # 复制到构建源码 include（libxtst 的 XTest.h 依赖 XInput.h）。
        _xi_inc = os.path.join(self.dependencies["libxi"].package_folder, "include")
        _xi_src = os.path.join(_xi_inc, "X11", "extensions", "XInput.h")
        if os.path.exists(_xi_src):
            for _inc in ("actions", "actiontools", "execution", "tools"):
                _dst = os.path.join(self.source_folder, _inc, "include", "X11", "extensions")
                os.makedirs(_dst, exist_ok=True)
                shutil.copy2(_xi_src, os.path.join(_dst, "XInput.h"))
            _dst3 = os.path.join(self.source_folder, "actiona", "3rdparty", "include", "X11", "extensions")
            os.makedirs(_dst3, exist_ok=True)
            shutil.copy2(_xi_src, os.path.join(_dst3, "XInput.h"))
        # qtbase(非变体) 的 qconfig.h 定义 QT_NO_DBUS=1/QT_NO_OPENSSL，污染
        # QtDBus/QxtSmtp 编译。临时注释（configure 前），构建后恢复。
        _qcfg = os.path.join(self.dependencies["qtbase"].package_folder, "include", "QtCore", "qconfig.h")
        _qcfg_bak = _qcfg + ".actiona_bak"
        if os.path.exists(_qcfg) and not os.path.exists(_qcfg_bak):
            _d = open(_qcfg, encoding="utf-8").read()
            open(_qcfg_bak, "w", encoding="utf-8").write(_d)
            _d = _d.replace("#define QT_NO_DBUS 1", "// #define QT_NO_DBUS 1")
            _d = _d.replace("#define QT_NO_OPENSSL", "// #define QT_NO_OPENSSL")
            open(_qcfg, "w", encoding="utf-8").write(_d)
        cmake.configure(variables={
            "CMAKE_PREFIX_PATH": prefix,
            # actiontools 的 Q_OS_UNIX 代码 include <X11/Xlib.h>/X11/X.h/XTest.h：
            # Xlib.h 由 libx11、X11/X.h 由 xorgproto、XTest.h 由 libxtst 提供，
            # 经 CMAKE_CXX_FLAGS -isystem 注入（不受 pkg_search_module 覆盖）。
            # 强制 qtbase-sql-dbus 的 include 前置：其 qconfig.h 无 QT_NO_DBUS，
            # 避免 QtCore/qconfig.h 从 qtbase(非变体) 加载导致 QtDBus 走 dummy 分支。
            "CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES": "{}/include/QtDBus;{}/include".format(
                self.dependencies["qtbase-sql-dbus"].package_folder,
                self.dependencies["qtbase-sql-dbus"].package_folder,
            ),
            "CMAKE_SHARED_LINKER_FLAGS": "-L{}/lib -lnotify -L{}/lib -lXtst -L{}/lib -lX11".format(
                self.dependencies["libnotify"].package_folder,
                self.dependencies["libxtst"].package_folder,
                self.dependencies["libx11"].package_folder,
            ),
            "CMAKE_EXE_LINKER_FLAGS": "-L{}/lib -lnotify -L{}/lib -lXtst -L{}/lib -lX11".format(
                self.dependencies["libnotify"].package_folder,
                self.dependencies["libxtst"].package_folder,
                self.dependencies["libx11"].package_folder,
            ),
            "CMAKE_CXX_FLAGS": " -UQT_NO_DBUS -DQ_OS_UNIX -isystem {}/actiontools/3rdparty/qtjsapi -isystem {}/actiontools/3rdparty/qtjsapi".format(
                self.build_folder, self.source_folder) + " ".join(
                " -isystem {}/include".format(p) for p in (
                    self.dependencies["qtbase-sql-dbus"].package_folder,
                    self.dependencies["qtbase-sql-dbus"].package_folder,
                    self.dependencies["qtbase-sql-dbus"].package_folder,
                    self.dependencies["libx11"].package_folder,
                    self.dependencies["libx11"].package_folder,
                    self.dependencies["libx11"].package_folder,
                    self.dependencies["xorgproto"].package_folder,
                    self.dependencies["libxtst"].package_folder,
                    self.dependencies["libxi"].package_folder,
                    self.dependencies["libxext"].package_folder,
                    self.dependencies["libxcb"].package_folder,
                    self.dependencies["qtbase-sql-dbus"].package_folder,
                    self.dependencies["libnotify"].package_folder,
                    self.dependencies["glib"].package_folder,
                ) if p
            ) + " -isystem {}/include/QtDBus -isystem {}/include/QtNetwork -isystem {}/include/glib-2.0 -isystem {}/lib/glib-2.0/include -isystem {}/include/gdk-pixbuf-2.0 -isystem {}/include/gdk-pixbuf-2.0".format(
                self.dependencies["qtbase-sql-dbus"].package_folder,
                self.dependencies["qtbase-sql-dbus"].package_folder,
                self.dependencies["glib"].package_folder,
                self.dependencies["glib"].package_folder,
                self.dependencies["gdk-pixbuf"].package_folder,
                self.dependencies["gdk-pixbuf"].package_folder,
            ),
        })
        # 加载 libQt6Core/libQt6Qml 等，注入依赖包 lib 路径（E004 先例）。
        qt_libs = os.pathsep.join(
            os.path.join(p, "lib")
            for p in (self.dependencies["qtbase"].package_folder,
                      self.dependencies["qttools"].package_folder,
                      self.dependencies["qtdeclarative"].package_folder)
            if p
        )
        try:
            self.run(
                # 显式 -j$(nproc) 并行（此前 -j1/裸 cmake --build 在 CI 3600s
                # 超时窗口内编译不完——make 默认串行；qtbase 等平台大包
                # 经 Conan CMake.build() helper 自动并行可过）。
                "cmake -E env LD_LIBRARY_PATH={} cmake --build \"{}\" -- -j$(nproc)".format(
                    shlex.quote(qt_libs), self.build_folder
                ),
                env="conanbuild",
            )
        finally:
            # 构建后恢复 qtbase(非变体) qconfig.h。
            _qcfg = os.path.join(self.dependencies["qtbase"].package_folder, "include", "QtCore", "qconfig.h")
            _qcfg_bak = _qcfg + ".actiona_bak"
            if os.path.exists(_qcfg_bak):
                import shutil as _sh
                _sh.copy2(_qcfg_bak, _qcfg)
                os.remove(_qcfg_bak)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
