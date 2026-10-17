#!/usr/bin/env python3
"""Conan recipe for qt-unixodbc 5.15.2 on OpenHarmony PC.

Builds the Qt5 SQL ODBC driver plugin (libqsqlodbc.so) from the qtbase
source tree. Because qt5-qtbase is configured with -no-feature-sql, the
Qt5Sql library is also built from source within this recipe.

unixODBC is vendored (built from source inside build()) because it is
not yet published to the conan registry. Only qt5-qtbase is declared as
a conan dependency (for Qt5Core, moc, and headers).
"""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import Autotools, AutotoolsToolchain


class QtUnixodbcConan(ConanFile):
    name = "qt-unixodbc"
    version = "5.15.2"
    description = "Qt5 unixODBC SQL driver plugin (QODBCDriver)"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Generate Autotools toolchain for unixODBC build
        # This sets CC, CXX, CFLAGS, CXXFLAGS, LDFLAGS correctly for OHOS
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-gui", "--enable-shared", "--enable-static",
        ])
        tc.generate()

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt-unixodbc only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        # Download qtbase source (contains SQL module + ODBC driver source)
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                break
            except Exception as error:
                self.output.warning(f"Failed to download qtbase source from {url}: {error}")
        else:
            raise ConanInvalidConfiguration("Unable to download qtbase source from all mirrors")

        # Download and extract unixODBC source into a subdirectory
        unixodbc_data = self.conan_data["unixodbc_sources"]
        odbc_urls = unixodbc_data["url"]
        if isinstance(odbc_urls, str):
            odbc_urls = [odbc_urls]
        odbc_dest = os.path.join(self.source_folder, "unixodbc")
        for url in odbc_urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=unixodbc_data["sha256"],
                    strip_root=True,
                    destination=odbc_dest,
                )
                break
            except Exception as error:
                self.output.warning(f"Failed to download unixODBC source from {url}: {error}")
        else:
            raise ConanInvalidConfiguration("Unable to download unixODBC source from all mirrors")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        # Get compiler from Conan profile (R33: no bare shell vars)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "qt-unixodbc requires c and cpp compiler executables from the Conan profile"
            )

        # qt5-qtbase conan package paths
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder
        qt5_inc = os.path.join(qt5_pkg, "include")
        qt5_lib = os.path.join(qt5_pkg, "lib")
        moc = os.path.join(qt5_pkg, "bin", "moc")

        # ── Step 1: Build vendored unixODBC ──
        unixodbc_src = os.path.join(src_dir, "unixodbc")
        unixodbc_install = os.path.join(self.build_folder, "unixodbc_install")

        # E011 fix: HMDFS umask 077 → 022 (use Python, avoid external sed)
        def _fix_umask(filepath):
            if os.path.isfile(filepath):
                content = open(filepath, "r", encoding="utf-8", errors="ignore").read()
                content = content.replace("umask 077", "umask 022")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

        configure_sh = os.path.join(unixodbc_src, "configure")
        _fix_umask(configure_sh)
        _fix_umask(os.path.join(unixodbc_src, "libltdl", "configure"))

        # Write OHOS-aware config.guess/config.sub (CI workers lack them)
        ohos_triplet = "aarch64-unknown-linux-ohos"
        for dest_dir in [unixodbc_src, os.path.join(unixodbc_src, "libltdl")]:
            if os.path.isfile(os.path.join(dest_dir, "configure")):
                cg_path = os.path.join(dest_dir, "config.guess")
                with open(cg_path, "w") as f:
                    f.write(f"#!/bin/sh\necho '{ohos_triplet}'\n")
                os.chmod(cg_path, 0o755)
                cs_path = os.path.join(dest_dir, "config.sub")
                with open(cs_path, "w") as f:
                    f.write('#!/bin/sh\necho "$1"\n')
                os.chmod(cs_path, 0o755)
                self.output.info(f"Wrote OHOS-aware config.guess/config.sub in {dest_dir}")

        configure_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/bin/sh"
        if not os.path.isfile(configure_shell):
            for candidate in ["/bin/bash", "/usr/bin/bash", "/data/service/hnp/bin/bash", "/bin/sh"]:
                if os.path.isfile(candidate):
                    configure_shell = candidate
                    break
            else:
                raise ConanInvalidConfiguration("A POSIX shell is required to build unixODBC")

        # Set CC/CXX and LDFLAGS for autotools configure (R33: from Conan profile)
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        # OHOS: C compiler needs system library paths to create executables
        if self.settings.os == "OHOS":
            existing_ldflags = os.environ.get("LDFLAGS", "")
            extra_ldflags = "-L/system/lib64 -L/vendor/lib64"
            os.environ["LDFLAGS"] = f"{existing_ldflags} {extra_ldflags}".strip()
            existing_cflags = os.environ.get("CFLAGS", "")
            os.environ["CFLAGS"] = f"{existing_cflags} -fPIC".strip()

        # Run configure/make/install using self.run() with cwd=unixodbc_src
        # Pass LDFLAGS/CFLAGS as configure args (more reliable than os.environ)
        ldflags = '-L/system/lib64 -L/vendor/lib64'
        cflags = '-fPIC'
        self.run(
            f'{shlex.quote(configure_shell)} ./configure --prefix="{unixodbc_install}" '
            f'--disable-gui --enable-shared --enable-static '
            f'CC="{cc}" CXX="{cxx}" CFLAGS="{cflags}" LDFLAGS="{ldflags}"',
            cwd=unixodbc_src
        )
        self.run('make -j2', cwd=unixodbc_src)
        self.run('make install', cwd=unixodbc_src)

        odbc_inc = os.path.join(unixodbc_install, "include")
        odbc_lib = os.path.join(unixodbc_install, "lib")

        # ── Step 2: Prepare include directory for QtSql config headers ──
        qtinc_dir = os.path.join(self.build_folder, "qtinc")
        qtsql_qtinc = os.path.join(qtinc_dir, "QtSql")
        os.makedirs(qtsql_qtinc, exist_ok=True)

        # Copy qtsql-config.h from the qt5-qtbase package
        qtsql_config = os.path.join(qt5_pkg, "src", "sql", "qtsql-config.h")
        if os.path.isfile(qtsql_config):
            shutil.copy2(qtsql_config, qtsql_qtinc)

        qtsql_config_p = os.path.join(qt5_pkg, "src", "sql", "qtsql-config_p.h")
        qtsql_private_qtinc = os.path.join(qtsql_qtinc, "private")
        os.makedirs(qtsql_private_qtinc, exist_ok=True)
        if os.path.isfile(qtsql_config_p):
            shutil.copy2(qtsql_config_p, qtsql_private_qtinc)

        # ── Step 3: Build Qt5Sql from source ──
        sql_src = os.path.join(src_dir, "src", "sql", "kernel")

        cflags = (
            f"-pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations "
            f"-D_REENTRANT -fPIC -DQT_NO_USING_NAMESPACE -DQT_NO_CAST_FROM_ASCII "
            f"-DQT_NO_FOREACH -DQT_NO_DEBUG -DQT_SQL_LIB -DQT_CORE_LIB"
        )

        includes = " ".join([
            f"-I{qtinc_dir}",
            f"-I{qt5_inc}",
            f"-I{os.path.join(qt5_inc, 'QtCore')}",
            f"-I{os.path.join(qt5_inc, 'QtCore', '5.15.2')}",
            f"-I{os.path.join(qt5_inc, 'QtCore', '5.15.2', 'QtCore')}",
            f"-I{os.path.join(qt5_inc, 'QtSql')}",
            f"-I{os.path.join(qt5_inc, 'QtSql', '5.15.2')}",
            f"-I{os.path.join(qt5_inc, 'QtSql', '5.15.2', 'QtSql')}",
            f"-I{os.path.join(qt5_pkg, 'src')}",
            f"-I{os.path.join(src_dir, 'include')}",
            f"-I{sql_src}",
            f"-I{os.path.join(src_dir, 'src', 'corelib')}",
            f"-I{self.build_folder}",
        ])

        # Run moc for Qt5Sql headers that need it
        moc_qsqldriver = os.path.join(self.build_folder, "moc_qsqldriver.cpp")
        self.run(f'"{moc}" -o "{moc_qsqldriver}" '
                 f'"{os.path.join(sql_src, "qsqldriver.h")}"')

        moc_qsqldriverplugin = os.path.join(self.build_folder, "moc_qsqldriverplugin.cpp")
        self.run(f'"{moc}" -o "{moc_qsqldriverplugin}" '
                 f'"{os.path.join(sql_src, "qsqldriverplugin.h")}"')

        # Compile Qt5Sql source files
        sql_sources = [
            "qsqlquery", "qsqldatabase", "qsqlfield", "qsqlrecord",
            "qsqldriver", "qsqldriverplugin", "qsqlerror",
            "qsqlresult", "qsqlindex", "qsqlcachedresult",
        ]
        for src_name in sql_sources:
            src_file = os.path.join(sql_src, f"{src_name}.cpp")
            obj_file = os.path.join(self.build_folder, f"{src_name}.o")
            self.run(f'"{cxx}" -c {cflags} {includes} "{src_file}" -o "{obj_file}"')

        # Compile moc output
        for moc_src in ["moc_qsqldriver", "moc_qsqldriverplugin"]:
            moc_file = os.path.join(self.build_folder, f"{moc_src}.cpp")
            obj_file = os.path.join(self.build_folder, f"{moc_src}.o")
            self.run(f'"{cxx}" -c {cflags} {includes} "{moc_file}" -o "{obj_file}"')

        # Link libQt5Sql.so
        sql_objs = " ".join(
            os.path.join(self.build_folder, f"{name}.o") for name in sql_sources
        )
        moc_objs = " ".join(
            os.path.join(self.build_folder, f"{name}.o")
            for name in ["moc_qsqldriver", "moc_qsqldriverplugin"]
        )
        libQt5Sql = os.path.join(self.build_folder, "libQt5Sql.so")
        self.run(
            f'"{cxx}" -shared -o "{libQt5Sql}" '
            f'{sql_objs} {moc_objs} '
            f'-L"{qt5_lib}" -lQt5Core '
            f'-Wl,-soname,libQt5Sql.so.5 -Wl,-rpath,"{qt5_lib}"'
        )

        # Create versioned copies (HMDFS doesn't support symlinks)
        for ver_name in ["libQt5Sql.so.5", "libQt5Sql.so.5.15", "libQt5Sql.so.5.15.2"]:
            ver_path = os.path.join(self.build_folder, ver_name)
            shutil.copy2(libQt5Sql, ver_path)

        # ── Step 4: Build ODBC driver plugin ──
        odbc_src = os.path.join(src_dir, "src", "plugins", "sqldrivers", "odbc")

        # Copy odbc.json (needed by moc for Q_PLUGIN_METADATA)
        shutil.copy2(
            os.path.join(odbc_src, "odbc.json"),
            os.path.join(self.build_folder, "odbc.json"),
        )

        # Run moc on qsql_odbc_p.h
        moc_qsql_odbc = os.path.join(self.build_folder, "moc_qsql_odbc.cpp")
        self.run(f'"{moc}" -o "{moc_qsql_odbc}" '
                 f'"{os.path.join(odbc_src, "qsql_odbc_p.h")}"')

        # Run moc on main.cpp → main.moc (included by main.cpp via #include "main.moc")
        main_moc = os.path.join(self.build_folder, "main.moc")
        self.run(f'"{moc}" "{os.path.join(odbc_src, "main.cpp")}" -o "{main_moc}"')

        # Compile ODBC plugin source files
        plugin_cflags = cflags + " -DQT_PLUGIN -DUNICODE"
        plugin_includes = includes + f" -I{odbc_inc}"

        # Compile qsql_odbc.cpp
        qsql_odbc_obj = os.path.join(self.build_folder, "qsql_odbc.o")
        self.run(f'"{cxx}" -c {plugin_cflags} {plugin_includes} '
                 f'"{os.path.join(odbc_src, "qsql_odbc.cpp")}" -o "{qsql_odbc_obj}"')

        # Compile main.cpp (includes main.moc)
        main_obj = os.path.join(self.build_folder, "main.o")
        self.run(f'"{cxx}" -c {plugin_cflags} {plugin_includes} '
                 f'"{os.path.join(odbc_src, "main.cpp")}" -o "{main_obj}"')

        # Compile moc_qsql_odbc.cpp
        moc_odbc_obj = os.path.join(self.build_folder, "moc_qsql_odbc.o")
        self.run(f'"{cxx}" -c {plugin_cflags} {plugin_includes} '
                 f'"{moc_qsql_odbc}" -o "{moc_odbc_obj}"')

        # Link libqsqlodbc.so
        libqsqlodbc = os.path.join(self.build_folder, "libqsqlodbc.so")
        self.run(
            f'"{cxx}" -shared -o "{libqsqlodbc}" '
            f'"{qsql_odbc_obj}" "{main_obj}" "{moc_odbc_obj}" '
            f'-L"{self.build_folder}" -lQt5Sql '
            f'-L"{qt5_lib}" -lQt5Core '
            f'-L"{odbc_lib}" -lodbc '
            f'-Wl,-soname,libqsqlodbc.so -Wl,-rpath,\'$ORIGIN/../lib\''
        )

    def package(self):
        # Copy the ODBC driver plugin
        copy(self, "libqsqlodbc.so",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "plugins", "sqldrivers"),
             keep_path=False)

        # Copy Qt5Sql library (built from source, not in qt5-qtbase)
        copy(self, "libQt5Sql.so*",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

        # Copy unixODBC libraries (vendored)
        unixodbc_install = os.path.join(self.build_folder, "unixodbc_install")
        if os.path.isdir(os.path.join(unixodbc_install, "lib")):
            copy(self, "libodbc.so*",
                 src=os.path.join(unixodbc_install, "lib"),
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)
            copy(self, "libodbcinst.so*",
                 src=os.path.join(unixodbc_install, "lib"),
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)
            copy(self, "libodbccr.so*",
                 src=os.path.join(unixodbc_install, "lib"),
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)

        # Copy unixODBC headers
        if os.path.isdir(os.path.join(unixodbc_install, "include")):
            copy(self, "*.h",
                 src=os.path.join(unixodbc_install, "include"),
                 dst=os.path.join(self.package_folder, "include", "unixODBC"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]

        # Qt5Sql component
        qt5sql = self.cpp_info.components["Qt5Sql"]
        qt5sql.libs = ["Qt5Sql"]
        qt5sql.includedirs = ["include"]
        qt5sql.requires = ["qt5-qtbase::Qt5Core"]

        # unixODBC component (vendored)
        odbc = self.cpp_info.components["odbc"]
        odbc.libs = ["odbc"]
        odbc.includedirs = ["include/unixODBC"]

        # ODBC driver plugin
        plugin = self.cpp_info.components["qsqlodbc"]
        plugin.libs = ["qsqlodbc"]
        plugin.libdirs = ["plugins/sqldrivers"]
        plugin.requires = ["Qt5Sql", "odbc", "qt5-qtbase::Qt5Core"]
