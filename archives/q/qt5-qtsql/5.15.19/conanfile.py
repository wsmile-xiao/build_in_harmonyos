#!/usr/bin/env python3
"""Conan recipe for qt5-qtsql 5.15.19 (Qt5 Sql module) on OpenHarmony PC.

独立 Sql 供给包：qt5/5.15.19 主包未含 Sql（-no-feature-sql），本包从同源
qtbase 5.15.19 单独构建 src/sql + qsqlite 插件，四件套全（libQt5Sql.so +
include/QtSql 头 + lib/cmake/Qt5Sql config + plugins/sqldrivers/libqsqlite.so）
——qt-unixodbc 只带 .so 缺头缺 config 的坑不重蹈。ABI 与 qt5/5.15.19 主包
一致（同源码同 configure 开关框架，唯一差异 -sql-sqlite）。
"""
import os
import shlex
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5QtsqlConan(ConanFile):
    name = "qt5-qtsql"
    version = "5.15.19"
    description = "Qt5 Sql module + QSQLITE driver (standalone supply for qt5/5.15.19)"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Qt5Core 运行时来自主包（闭包带出）；zlib 同主包
        self.requires("qt5/5.15.19")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt5-qtsql only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                break
            except ConanException as error:
                self.output.warning(f"Failed to download Qt5 source from {url}: {error}")
        else:
            raise ConanInvalidConfiguration("Unable to download Qt5 source from all mirrors")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "qt5-qtsql requires c and cpp compiler executables from the Conan profile"
            )

        zlib = self.dependencies["zlib"]
        zlib_inc = os.path.join(zlib.package_folder, "include")
        zlib_lib = os.path.join(zlib.package_folder, "lib")

        build_env = Environment()
        build_env.define("CC", cc)
        build_env.define("CXX", cxx)
        build_env.append("CFLAGS", f"-I{zlib_inc}")
        build_env.append("CXXFLAGS", f"-I{zlib_inc}")
        build_env.append("LDFLAGS", f"-L{zlib_lib}")

        with build_env.vars(self).apply():
            configure_shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
            if not configure_shell:
                raise ConanInvalidConfiguration("A POSIX shell is required to run Qt configure")
            # 与 qt5/5.15.19 主包同框架；差异仅 sql 开启（qtbase 内置 sqlite，
            # -sql-sqlite 不引外部依赖）。跳过非必需大件以缩短构建（sql 只需
            # corelib 前置）：-nomake tools 系列按需，widgets/gui/sql 侧最小化。
            self.run(
                f'cd "{src_dir}" && {shlex.quote(configure_shell)} ./configure '
                f'-prefix "{self.package_folder}" '
                f'-opensource -confirm-license '
                f'-no-dbus -no-accessibility '
                f'-opengl es2 -no-xcb -no-eglfs -no-linuxfb '
                f'-sql-sqlite '
                f'-no-feature-systemsemaphore -no-feature-sharedmemory '
                f'-nomake tests -nomake examples '
                f'-no-iconv -no-glib -no-icu -no-vulkan '
                f'-no-openssl -no-libproxy -no-system-proxies '
                f'-system-zlib '
                f'-platform linux-clang '
                f'-skip qttools -skip qtsvg -skip qtdeclarative -skip qtlocation '
                f'-skip qtmultimedia -skip qtserialport -skip qttranslations '
                f'-recheck-all',
            )
            # OHOS 禁 mkfifo jobserver：make -j1
            self.run(f'cd "{src_dir}" && make -j1 QMAKE_STRIP=""')

    def package(self):
        # qt in-source 构建：lib/plugins/include/cmake 全部就地生成在
        # source_folder（qtbase configure 在源码树根跑，产物 b/lib 等）
        src_dir = self.source_folder
        # 四件套定向打包（不整树拷贝，避免夹带主包已供组件）
        # 1) libQt5Sql.so（含 .so.5/.so.5.15.19 符号链与实体全收）
        lib_dir = os.path.join(src_dir, "lib")
        if os.path.isdir(lib_dir):
            for f in os.listdir(lib_dir):
                if f.startswith("libQt5Sql.so"):
                    copy(self, f, src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 2) include/QtSql：构建树内源码在 {build}/b（in-source 就地构建），
        # include 同样生成在 build 顶层 include/（qtbase 前向头）与 b/include
        inc = os.path.join(src_dir, "include", "QtSql")
        if os.path.isdir(inc):
            copy(self, "*", src=inc, dst=os.path.join(self.package_folder, "include", "QtSql"), keep_path=True)
        # include/QtCore 里 sql 依赖的公共宏（qconfig.h/qglobal.h 等 QtSql 头会拉）
        qinc = os.path.join(src_dir, "include", "QtCore")
        if os.path.isdir(qinc):
            copy(self, "*.h", src=qinc, dst=os.path.join(self.package_folder, "include", "QtCore"), keep_path=False)
        # 3) lib/cmake/Qt5Sql config
        cmake_sql = os.path.join(src_dir, "lib", "cmake", "Qt5Sql")
        if os.path.isdir(cmake_sql):
            copy(self, "*", src=cmake_sql, dst=os.path.join(self.package_folder, "lib", "cmake", "Qt5Sql"), keep_path=True)
        # Qt5 config 基础文件（Qt5SqlConfig 依赖的 Qt5Config 共享段）
        cmake_base = os.path.join(src_dir, "lib", "cmake", "Qt5")
        if os.path.isdir(cmake_base):
            copy(self, "Qt5Config*", src=cmake_base, dst=os.path.join(self.package_folder, "lib", "cmake", "Qt5"), keep_path=True)
            copy(self, "Qt5ModuleLocation*", src=cmake_base, dst=os.path.join(self.package_folder, "lib", "cmake", "Qt5"), keep_path=True)
        # 4) qsqlite 驱动插件
        sqldrv = os.path.join(src_dir, "plugins", "sqldrivers")
        if os.path.isdir(sqldrv):
            copy(self, "*.so*", src=sqldrv, dst=os.path.join(self.package_folder, "plugins", "sqldrivers"), keep_path=False)
        # sqlite3 运行库（qtbase 内置编进插件，无需单独分发；若为动态形态则带上）
        for f in os.listdir(lib_dir) if os.path.isdir(lib_dir) else []:
            if f.startswith("libQt5Sql"):
                continue
            if "sqlite" in f.lower() and f.endswith(".so"):
                copy(self, f, src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # mkspecs（qmake 消费者可能要）
        mkspecs_dir = os.path.join(src_dir, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "qconfig.pri", src=mkspecs_dir, dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)
            copy(self, "modules", src=mkspecs_dir, dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        qt5sql = self.cpp_info.components["Qt5Sql"]
        qt5sql.libs = ["Qt5Sql"]
        qt5sql.includedirs = ["include", "include/QtSql"]
        qt5sql.requires = ["qt5::Qt5Core", "zlib::zlib"]
        qt5sql.set_property("cmake_file_name", "Qt5Sql")
        qt5sql.set_property("cmake_target_name", "Qt5::Sql")
