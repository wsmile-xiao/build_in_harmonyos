#!/usr/bin/env python3
"""Conan recipe — kdoctools 6.19.0（KDE DocBook 文档处理工具）.

kdoctools 提供 meinproc/meinproc5 等工具，将 DocBook XML 文档转换为
HTML/Man/Info 等格式，供 KDE 帮助系统使用。
构建系统：CMake
平台：OHOS aarch64 / Linux / macOS
依赖：ECM、Qt6Core（qtbase）、libxml2、libxslt
已知限制：KF6Archive 未合入（karchive 无 Conan 配方），采用 KDE 官方
MEINPROC_NO_KARCHIVE 降级（meinproc cache 选项不可用，DocBook 转换正常）；
KF6I18n 为 OPTIONAL（翻译功能，跳过）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KDocToolsConan(ConanFile):
    name = "kdoctools"
    version = "6.19.0"
    description = "kdoctools — KDE DocBook documentation processing tools"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdoctools"
    url = "https://invent.kde.org/frameworks/kdoctools"
    package_type = "application"
    exports_sources = "patches/*"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("extra-cmake-modules/6.19.0")
        self.requires("qtbase/6.11.1")
        # karchive/6.19.0 已合入（PR #4636）——meinproc cache 选项完整可用
        self.requires("karchive/6.19.0")
        # karchive 的 KF6ArchiveConfig.cmake find_dependency(OpenSSL)（CI
        # #24170 报 OpenSSL 找不到——kdoctools 未声明 openssl 依赖）
        self.requires("openssl/3.5.6.1")
        # libxml2 用 2.15.3：与 libxslt/1.1.45.1 的依赖版本一致，避免版本冲突
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # CI #23910：qtpaths_target.cmake 预定义 Qt6::qtpaths 与 Qt6CoreTools
        # 的 export set 冲突（Some but not all targets already defined——
        # syncqt/moc/rcc 等未定义）——qtbase 包的 Qt6CoreTools 已提供
        # Qt6::qtpaths（Qt6CoreToolsTargets.cmake）——移除预定义注入，
        # 让 Qt6CoreTools 完整定义（ECMQueryQt 的 Qt6::qtpaths 由 qtbase 提供）
        qtbase_pkg = self.dependencies["qtbase"].package_folder

        tc = CMakeToolchain(self)
        # karchive/6.19.0 已合入（PR #4636）——移除 MEINPROC_NO_KARCHIVE
        # 降级——meinproc cache 选项完整可用
        # ECM 的 KDEMetaInfoPlatformCheck 不认 HarmonyOS 平台（仅支持
        # Linux/FreeBSD/Windows/macOS），KDE 官方提供 KF_IGNORE_PLATFORM_CHECK
        # 变量绕过平台检查
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "true"
        # qtbase cmake_find_mode=none（自带 Qt6Config.cmake 在 lib/cmake/），
        # CMakeDeps 不生成 Qt6CoreConfig.cmake；显式设置 Qt6_DIR 与
        # Qt6Core_DIR 指向 qtbase 的 config 目录：find_package(Qt6) 用 Qt6_DIR，
        # find_package(Qt6Core)（kdoctools CMakeLists 独立组件查找）用 Qt6Core_DIR。
        # 兼容两种布局：标准 Qt6 安装为 lib/cmake/Qt6/Qt6Config.cmake（多一层
        # 子目录），扁平布局为 lib/cmake/Qt6Config.cmake；检测 Qt6 子目录优先
        qtbase_cmake = os.path.join(qtbase_pkg, "lib", "cmake")
        if os.path.isdir(os.path.join(qtbase_cmake, "Qt6")):
            qtbase_cmake = os.path.join(qtbase_cmake, "Qt6")
        tc.cache_variables["Qt6_DIR"] = qtbase_cmake
        # Qt6CoreConfig.cmake 在独立的 Qt6Core 子目录（CI #24015 报
        # Qt6Core 找不到——Qt6Core_DIR 指向 lib/cmake/Qt6 错误）——
        # Qt6Core_DIR 单独检测 Qt6Core 子目录（兼容标准/扁平布局）
        qtbase_core = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib", "cmake"
        )
        if os.path.isdir(os.path.join(qtbase_core, "Qt6Core")):
            qtbase_core = os.path.join(qtbase_core, "Qt6Core")
        tc.cache_variables["Qt6Core_DIR"] = qtbase_core
        # karchive 提供 KF6ArchiveConfig.cmake（CI #24016 报 KF6Archive
        # 找不到——CMakeLists.txt:49 find_package(KF6Archive 6.19.0)——
        # kdoctools 未设置 KF6Archive_DIR）——指向 karchive 包的配置目录
        karchive_cmake = os.path.join(
            self.dependencies["karchive"].package_folder, "lib", "cmake"
        )
        if os.path.isdir(os.path.join(karchive_cmake, "KF6Archive")):
            karchive_cmake = os.path.join(karchive_cmake, "KF6Archive")
        tc.cache_variables["KF6Archive_DIR"] = karchive_cmake
        # ECM 打包产物缺 ecm_uninstall.cmake.in，ECMUninstallTarget 的
        # configure_file 会失败；用 KDE 官方 KDE_SKIP_UNINSTALL_TARGET
        # 跳过 uninstall target 生成
        tc.variables["KDE_SKIP_UNINSTALL_TARGET"] = "TRUE"
        # ECM 打包产物也缺 ECMVersionHeader.h.in（package() 仅复制
        # *.cmake/*.py，漏 *.in 模板），ECMSetupVersion 的 configure_file
        # 会失败且无 KDE 官方跳过开关；此处用 ECM 源码自带模板内容生成缺失
        # 文件（if-not-exists 保护：ECM 打包修复后自动不生效，不影响其他 PR）
        ecm_modules = os.path.join(
            self.dependencies["extra-cmake-modules"].package_folder,
            "share", "ECM", "modules",
        )
        ecm_version_template = os.path.join(ecm_modules, "ECMVersionHeader.h.in")
        if not os.path.exists(ecm_version_template):
            with open(ecm_version_template, "w") as f:
                f.write(
                    "// This file was generated by ecm_setup_version(): DO NOT EDIT!\n\n"
                    "#ifndef @HEADER_PREFIX@_VERSION_H\n"
                    "#define @HEADER_PREFIX@_VERSION_H\n\n"
                    "#define @HEADER_PREFIX@_VERSION_STRING \"@HEADER_VERSION@\"\n"
                    "#define @HEADER_PREFIX@_VERSION_MAJOR @HEADER_VERSION_MAJOR@\n"
                    "#define @HEADER_PREFIX@_VERSION_MINOR @HEADER_VERSION_MINOR@\n"
                    "#define @HEADER_PREFIX@_VERSION_PATCH @HEADER_VERSION_PATCH@\n"
                    "#define @HEADER_PREFIX@_VERSION ((@HEADER_VERSION_MAJOR@<<16)"
                    "|(@HEADER_VERSION_MINOR@<<8)|(@HEADER_VERSION_PATCH@))\n\n#endif\n"
                )
        # ECM 打包产物缺 ECMQtDeclareLoggingCategory.cpp.in（package() 仅
        # 复制 *.cmake/*.py，漏 *.in 模板），ECMQtDeclareLoggingCategory 的
        # configure_file 会失败（CI #24350）——生成缺失模板（if-not-exists 保护）
        ecm_logging_template = os.path.join(ecm_modules, "ECMQtDeclareLoggingCategory.cpp.in")
        if not os.path.exists(ecm_logging_template):
            with open(ecm_logging_template, "w") as f:
                f.write(
                    "// This file was generated by ecm_qt_declare_logging_category(): DO NOT EDIT!\n\n"
                    "#include \"@HEADER_NAME@\"\n\n"
                    "@OPEN_NAMESPACES@\n"
                    "Q_LOGGING_CATEGORY(@IDENTIFIER@, \"@ARG_CATEGORY_NAME@\", Qt@ARG_DEFAULT_SEVERITY@Msg)\n"
                    "@CLOSE_NAMESPACES@\n"
                )
        # ECM 打包产物同样缺 ECMQtDeclareLoggingCategory.h.in（CI #24362——
        # configure_file 报 .h.in 缺失）——生成缺失模板（if-not-exists 保护）
        ecm_logging_header = os.path.join(ecm_modules, "ECMQtDeclareLoggingCategory.h.in")
        if not os.path.exists(ecm_logging_header):
            with open(ecm_logging_header, "w") as f:
                f.write(
                    "// This file was generated by ecm_qt_declare_logging_category(): DO NOT EDIT!\n\n"
                    "#ifndef @GUARD_NAME@\n"
                    "#define @GUARD_NAME@\n\n"
                    "#include <QLoggingCategory>\n"
                    "@OPEN_NAMESPACES@\n"
                    "Q_DECLARE_LOGGING_CATEGORY(@IDENTIFIER@)\n"
                    "@CLOSE_NAMESPACES@\n\n"
                    "#endif\n"
                )
        # CI #24400：karchive 的 KF6ArchiveTargets 链接接口含
        # PkgConfig::LibZstd——pkg_check_modules(LibZstd libzstd) 需
        # PKG_CONFIG_PATH 找到 libzstd.pc（zstd 包提供）——设置
        self.buildenv.append(
            "PKG_CONFIG_PATH",
            os.path.join(self.dependencies["zstd"].package_folder, "lib", "pkgconfig"),
        )
        # CI #24689：docbookl10nhelper 链接后运行失败（Error loading
        # shared library libQt6Core.so.6——LD_LIBRARY_PATH 未设置——
        # qtbase 包的 lib 有 libQt6Core.so.6）——设置 LD_LIBRARY_PATH
        self.buildenv.append(
            "LD_LIBRARY_PATH",
            os.path.join(self.dependencies["qtbase"].package_folder, "lib"),
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "KF6DocTools")
        self.cpp_info.set_property("cmake_target_name", "KF6::DocTools")