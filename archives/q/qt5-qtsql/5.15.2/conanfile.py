"""复用同版本 QtCore，独立构建 QtSql、模型类和 QSQLITE 插件。"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QtSqlConan(ConanFile):
    name = "qt5-qtsql"
    version = "5.15.2"
    description = "Qt5 SQL 模块、SQL 模型及 SQLite 驱动"
    license = "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-5/qtsql-index.html"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "shared-library"

    def requirements(self):
        """声明同版 QtCore 和外部 SQLite，避免重复构建或打包 QtCore。"""
        self.requires("qt5-qtbase/5.15.2.2", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.53.4")

    def validate(self):
        """限定已验证的原生发布构建，避免跨主机运行鸿蒙工具。"""
        if str(self.settings.os) not in ("Linux", "OHOS") or not can_run(self):
            raise ConanInvalidConfiguration("本配方需要 Linux/OHOS 原生构建环境")
        if str(self.settings.build_type) != "Release":
            raise ConanInvalidConfiguration("本配方匹配已发布的 Release QtBase")

    def export_sources(self):
        """将上游测试兼容补丁纳入源码导出。"""
        export_conandata_patches(self)

    def layout(self):
        """分离只读源码、构建目录和包安装目录。"""
        basic_layout(self)

    def source(self):
        """下载与 QtBase 同版的官方源码并校验摘要。"""
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _environment(self):
        """提供构建工具和测试所需的包路径，使用无头 Qt 平台插件。"""
        build = Path(self.build_folder)
        qt = Path(self.dependencies["qt5-qtbase"].package_folder)
        env = os.environ.copy()
        libraries = [str(build / "lib")]
        libraries.extend(str(Path(dep.package_folder) / "lib")
                         for dep in self.dependencies.host.values())
        env["LD_LIBRARY_PATH"] = ":".join(libraries + [env.get("LD_LIBRARY_PATH", "")])
        env["QMAKEPATH"] = str(build / "qt-host")
        env["QMAKEFEATURES"] = str(build / "qt-host/mkspecs/features")
        env["QT_PLUGIN_PATH"] = ":".join((str(build / "plugins"), str(qt / "plugins")))
        env["QT_QPA_PLATFORM"] = "offscreen"
        return env

    def _prepare_build(self):
        """在独立目录重定位 Qt 元数据，并配置 SQL 的真实可用功能。"""
        source, build = Path(self.source_folder), Path(self.build_folder)
        qt = Path(self.dependencies["qt5-qtbase"].package_folder)
        compat = build / "qt-host"
        shutil.copytree(qt / "mkspecs", compat / "mkspecs", dirs_exist_ok=True)
        functions = compat / "mkspecs/features/qt_functions.prf"
        functions.write_text(functions.read_text().replace(
            "Linux|FreeBSD|OpenBSD|NetBSD|DragonFly|SunOS|HP-UX|QNX|GNU",
            "Linux|FreeBSD|OpenBSD|NetBSD|DragonFly|SunOS|HP-UX|QNX|GNU|HarmonyOS|OHOS"))
        prefix = "\n".join(f"QT_MODULE_{key}_BASE = {qt / value}"
                           for key, value in (("BIN", "bin"), ("INCLUDE", "include"),
                                              ("LIB", "lib"), ("HOST_LIB", "lib"))) + "\n"
        for metadata in (compat / "mkspecs/modules-inst").glob("*.pri"):
            (compat / "mkspecs/modules" / metadata.name).write_text(prefix + metadata.read_text())
        core = (compat / "mkspecs/modules-inst/qt_lib_core.pri").read_text()
        if "itemmodel" not in core:
            raise ConanInvalidConfiguration("QtCore 必须启用 itemmodel 才能构建 SQL 模型")
        module = compat / "mkspecs/qmodule.pri"
        module.write_text(module.read_text().replace(" release_tools sql ", " release_tools ")
                          + "\nQT.global_private.enabled_features += sql\n")
        (compat / "qt.conf").write_text(
            f"[Paths]\nPrefix={qt}\nHostPrefix={qt}\nHostData={compat}\nData={compat}\n"
            f"HostBinaries={qt / 'bin'}\nTargetSpec=linux-clang\nHostSpec=linux-clang\n")
        (build / ".qmake.cache").write_text(f"QT_SOURCE_TREE = {source}\nQT_BUILD_TREE = {build}\n")
        sql = build / "src/sql"
        sql.mkdir(parents=True, exist_ok=True)
        (sql / "qtsql-config.pri").write_text(
            "QT.sql.enabled_features = sqlmodel\nQT.sql.disabled_features =\n")
        (sql / "qtsql-config.h").write_text("#define QT_FEATURE_sqlmodel 1\n")
        (sql / "qtsql-config_p.h").write_text("/* SQL 模块没有私有功能开关。 */\n")

    def _build_project(self, relative, env):
        """使用上游 qmake 工程串行构建，保存日志并传播任何错误。"""
        source, build = Path(self.source_folder), Path(self.build_folder)
        qt = Path(self.dependencies["qt5-qtbase"].package_folder)
        project = Path(relative)
        output = build / project.parent
        output.mkdir(parents=True, exist_ok=True)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc, cxx = compilers.get("c", "clang"), compilers.get("cpp", "clang++")
        args = [str(qt / "bin/qmake"), "-qtconf", str(build / "qt-host/qt.conf"),
                str(source / project), "CONFIG+=force_independent", "CONFIG-=precompile_header",
                f"QMAKE_CC={cc}", f"QMAKE_CXX={cxx}", f"QMAKE_LINK={cxx}",
                f"QT_TOOL.moc.binary={qt / 'bin/moc'}", f"QT_TOOL.rcc.binary={qt / 'bin/rcc'}",
                "QMAKE_LN_SHLIB=cp -p"]
        shell = shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("缺少 POSIX sh")
        log_path = output / "build.log"
        with log_path.open("w") as log:
            for command in (args, [shutil.which("make"), "-j1", f"SHELL={shell}"]):
                result = subprocess.run(command, cwd=output, env=env,
                                        stdout=log, stderr=subprocess.STDOUT)
                if result.returncode:
                    log.flush()
                    raise ConanInvalidConfiguration(log_path.read_text()[-7000:])
        return output

    def build(self):
        """构建 SQL 与 SQLite 插件，并运行全部 13 个 SQL 上游测试。"""
        source, build = Path(self.source_folder), Path(self.build_folder)
        self._prepare_build()
        env = self._environment()
        self._build_project("src/sql/sql.pro", env)
        for metadata in (build / "mkspecs/modules").glob("*sql*.pri"):
            shutil.copy2(metadata, build / "qt-host/mkspecs/modules" / metadata.name)
        sqlite = Path(self.dependencies["sqlite3"].package_folder)
        drivers = build / "src/plugins/sqldrivers"
        drivers.mkdir(parents=True, exist_ok=True)
        (drivers / "qtsqldrivers-config.pri").write_text(
            "QT.sqldrivers_private.enabled_features = sql-sqlite system-sqlite\n"
            "QT.sqldrivers_private.disabled_features = sql-db2 sql-ibase sql-mysql "
            "sql-oci sql-odbc sql-psql sql-sqlite2 sql-tds\n"
            f"QMAKE_INCDIR_SQLITE = {sqlite / 'include'}\n"
            f"QMAKE_LIBS_SQLITE = {sqlite / 'lib/libsqlite3.a'} -ldl -lpthread -lm\n")
        self._build_project("src/plugins/sqldrivers/sqlite/sqlite.pro", env)
        results = []
        for project in sorted((source / "tests/auto/sql").rglob("*.pro")):
            target = re.search(r"^TARGET\s*=\s*(\w+)", project.read_text(), re.M)
            if not target:
                continue
            name = target.group(1)
            output = self._build_project(project.relative_to(source), env)
            with (output / "test.log").open("w") as log:
                result = subprocess.run([str(output / name), "-o", "-,txt", "-o", "test.xml,xml"],
                                        cwd=output, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=180)
            text = (output / "test.log").read_text()
            summary = next((line for line in text.splitlines() if line.startswith("Totals:")), "无汇总")
            self.output.info(f"{name}: {summary}")
            results.append({"name": name, "exit_code": result.returncode, "summary": summary})
            (build / "upstream-tests.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            if result.returncode:
                raise ConanInvalidConfiguration(text[-7000:])
        if len(results) != 13:
            raise ConanInvalidConfiguration("SQL 上游测试清单发生变化，需要重新核验")

    def package(self):
        """安装 SQL 自身产物及可重定位头文件，不夹带 QtCore。"""
        source, build, package = map(Path, (self.source_folder, self.build_folder, self.package_folder))
        for p in (build / "lib").glob("libQt5Sql.so*"):
            target = package / "lib" / p.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target, follow_symlinks=True)
        plugin = package / "plugins/sqldrivers/libqsqlite.so"
        plugin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(build / "plugins/sqldrivers/libqsqlite.so", plugin)
        headers = (source / "include/QtSql/headers.pri").read_text()
        destination = package / "include/QtSql"
        destination.mkdir(parents=True, exist_ok=True)
        for field, folder, base in (
            ("HEADER_FILES", destination, source / "src/sql"),
            ("GENERATED_HEADER_FILES", destination, source / "include/QtSql"),
            ("PRIVATE_HEADER_FILES", destination / "5.15.2/QtSql/private", source / "src/sql"),
        ):
            names = re.search(rf"^SYNCQT\.{field}\s*=\s*(.*)$", headers, re.M).group(1).split()
            folder.mkdir(parents=True, exist_ok=True)
            for name in names:
                shutil.copy2(base / name, folder / Path(name).name)
        shutil.copy2(build / "include/QtSql/QtSqlDepends", destination / "QtSqlDepends")
        shutil.copy2(build / "src/sql/qtsql-config.h", destination / "qtsql-config.h")
        shutil.copy2(build / "src/sql/qtsql-config_p.h", destination / "5.15.2/QtSql/private/qtsql-config_p.h")
        licenses = package / "licenses"
        licenses.mkdir(exist_ok=True)
        for p in source.glob("LICENSE*"):
            if p.is_file():
                shutil.copy2(p, licenses / p.name)

    def package_info(self):
        """导出 Qt5::Sql 目标、QtCore 依赖和 SQLite 插件运行路径。"""
        self.cpp_info.libs = ["Qt5Sql"]
        self.cpp_info.includedirs = ["include", "include/QtSql"]
        self.cpp_info.defines = ["QT_SQL_LIB"]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "sqlite3::sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "Qt5Sql")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Sql")
        self.runenv_info.prepend_path("QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins"))
