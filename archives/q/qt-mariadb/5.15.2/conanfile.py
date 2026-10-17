#!/usr/bin/env python3
"""Conan recipe for qt-mariadb 5.15.2 — Qt5 MariaDB SQL driver plugin.

Builds the QMYSQL/QMARIADB driver plugin (libqsqlmysql.so) from the
qtbase source tree's src/plugins/sqldrivers/mysql/ directory, linking
against libmariadb instead of libmysqlclient.

The plugin source files are included directly in the recipe (src/ dir)
to avoid downloading the 50 MB qtbase tarball for just 4 files. The
upstream source URL is declared in conandata.yml for traceability
(R39). The source files are unmodified from the upstream qtbase 5.15.2
release.

The plugin is a shared library loaded at runtime by Qt5Sql via dlopen.
Qt5Sql symbols are left unresolved at link time (standard for Qt
plugins on Linux/OHOS — the host application provides them when the
plugin is loaded).
"""
import os
import shutil
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QtMariadbConan(ConanFile):
    name = "qt-mariadb"
    version = "5.15.2"
    description = "Qt5 MariaDB SQL driver plugin (QMYSQLDriver with MariaDB backend)"
    license = "LGPL-3.0"
    homepage = "https://download.qt.io/archive/qt/5.15/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    exports_sources = "src/*", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        self.requires("mariadb-connector-c/3.4.8")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt-mariadb only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        # Plugin source files are included via exports_sources.
        # The upstream URL is declared in conandata.yml for traceability (R39).
        pass

    def build(self):
        # No patches declared yet (conandata.yml patches is empty) — this call
        # is a no-op kept so patches can be added without touching build().
        apply_conandata_patches(self)

        # --- Resolve dependency paths ---
        qt5 = self.dependencies["qt5-qtbase"]
        mariadb = self.dependencies["mariadb-connector-c"]

        qt_pkg = qt5.package_folder
        qt_include = os.path.join(qt_pkg, "include")
        qt_src = os.path.join(qt_pkg, "src")
        qt_lib = os.path.join(qt_pkg, "lib")
        qt_bin = os.path.join(qt_pkg, "bin")

        mdb_pkg = mariadb.package_folder
        mdb_inc = os.path.join(mdb_pkg, "include", "mariadb")
        mdb_lib = os.path.join(mdb_pkg, "lib", "mariadb")

        # Plugin source is included via exports_sources
        plugin_src = os.path.join(self.source_folder, "src")

        # --- Create missing QtSql config forwarding headers ---
        # The qt5-qtbase package was built with -no-feature-sql, so the
        # generated config headers exist in src/sql/ but their forwarding
        # headers in include/QtSql/ are missing.
        build_inc_qtsql = os.path.join(self.build_folder, "qt-include", "QtSql")
        build_inc_qtsql_priv = os.path.join(build_inc_qtsql, "private")
        os.makedirs(build_inc_qtsql_priv, exist_ok=True)
        build_inc = os.path.join(self.build_folder, "qt-include")

        config_files = [
            ("qtsql-config.h", os.path.join(qt_src, "sql", "qtsql-config.h"), build_inc_qtsql),
            ("qtsql-config_p.h", os.path.join(qt_src, "sql", "qtsql-config_p.h"), build_inc_qtsql),
            ("qtsql-config_p.h", os.path.join(qt_src, "sql", "qtsql-config_p.h"), build_inc_qtsql_priv),
        ]
        for fname, src_path, dst_dir in config_files:
            if os.path.isfile(src_path):
                dst = os.path.join(dst_dir, fname)
                if not os.path.isfile(dst):
                    shutil.copy2(src_path, dst)
                    self.output.info(f"Created forwarding header: {dst_dir}/{fname}")

        # --- Compiler ---
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx") or "clang++"

        # --- Step 1: Run moc on main.cpp to generate main.moc ---
        moc = os.path.join(qt_bin, "moc")
        if not os.path.isfile(moc):
            raise ConanInvalidConfiguration(
                f"moc tool not found at {moc}"
            )

        moc_inc = [
            f"-I{build_inc}",
            f"-I{qt_include}",
            f"-I{qt_include}/QtCore",
            f"-I{qt_include}/QtSql",
            f"-I{plugin_src}",
        ]
        moc_cmd = (
            f"{shlex.quote(moc)} "
            f"{' '.join(moc_inc)} "
            f"{shlex.quote(os.path.join(plugin_src, 'main.cpp'))} "
            f"-o {shlex.quote(os.path.join(plugin_src, 'main.moc'))}"
        )
        self.output.info(f"Running moc: {moc_cmd}")
        self.run(moc_cmd)

        # --- Step 2: Compile plugin source files ---
        defines = [
            "-D_REENTRANT",
            "-DQT_NO_CAST_TO_ASCII",
            "-DQT_NO_CAST_FROM_ASCII",
            "-DQT_NO_DEBUG",
            "-DQT_PLUGIN",
            "-DQT_SQL_LIB",
            "-DQT_CORE_LIB",
        ]
        if self.settings.os == "OHOS":
            # Keep in sync with how the qt5-qtbase/5.15.2 package was built
            # (its qconfig defines Q_OS_OHOS); the plugin source itself has no
            # OHOS-specific branches.
            defines.append("-DQ_OS_OHOS")

        include_flags = [
            f"-I{build_inc}",
            f"-I{plugin_src}",
            f"-I{qt_include}",
            f"-I{qt_include}/QtCore",
            f"-I{qt_include}/QtCore/5.15.2",
            f"-I{qt_include}/QtCore/5.15.2/QtCore",
            f"-I{qt_include}/QtSql",
            f"-I{qt_include}/QtSql/5.15.2",
            f"-I{qt_include}/QtSql/5.15.2/QtSql",
            f"-I{qt_src}/sql/kernel",
            f"-I{qt_src}/corelib/kernel",
            f"-I{qt_src}/corelib/animation",
            f"-I{qt_src}/corelib/global",
            f"-I{mdb_inc}",
        ]

        cxx_flags = [
            "-c", "-pipe", "-O2", "-std=c++14",
            "-Wall", "-Wextra",
            "-Wno-deprecated-declarations",
            "-fPIC",
        ] + defines + include_flags

        # Compile qsql_mysql.cpp
        self.run(
            f"{shlex.quote(cxx)} {' '.join(cxx_flags)} "
            f"{shlex.quote(os.path.join(plugin_src, 'qsql_mysql.cpp'))} "
            f"-o qsql_mysql.o"
        )

        # Compile main.cpp
        self.run(
            f"{shlex.quote(cxx)} {' '.join(cxx_flags)} "
            f"{shlex.quote(os.path.join(plugin_src, 'main.cpp'))} "
            f"-o main.o"
        )

        # --- Step 3: Link into libqsqlmysql.so ---
        # Qt5Sql symbols are intentionally left unresolved — the plugin
        # is loaded at runtime by Qt5Sql which provides them.
        link_flags = [
            "-shared",
            "-o", "libqsqlmysql.so",
            "qsql_mysql.o", "main.o",
            f"-L{qt_lib}",
            "-lQt5Core",
            f"-L{mdb_lib}",
            "-lmariadb",
            "-Wl,-soname,libqsqlmysql.so",
        ]
        self.run(f"{shlex.quote(cxx)} {' '.join(link_flags)}")

        self.output.info("Built libqsqlmysql.so")

    def package(self):
        plugin_dst = os.path.join(self.package_folder, "plugins", "sqldrivers")
        os.makedirs(plugin_dst, exist_ok=True)
        src = os.path.join(self.build_folder, "libqsqlmysql.so")
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(plugin_dst, "libqsqlmysql.so"))

    def package_info(self):
        self.cpp_info.libdirs = ["plugins/sqldrivers"]
        self.cpp_info.libs = ["qsqlmysql"]
