#!/usr/bin/env python3
"""Conan recipe for GNUstep SQLClient 1.9.0 (SQL database access framework)."""

import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# OHOS 系统运行库目录（本平台硬编码，来源: OHOS NDK 默认安装布局）。
_OHOS_SYSTEM_LIBDIRS = (
    "/system/lib64",
    "/system/lib64/ndk",
    "/data/storage/el1/bundle/libs/arm64",
)


class SQLClientConan(ConanFile):
    name = "sqlclient"
    version = "1.9.0"
    description = "GNUstep SQLClient library: simple interface to SQL databases"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnustep.github.io/"
    url = "https://github.com/gnustep/libs-sqlclient"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sqlclient is prepared for Linux/OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 核心库依赖 gnustep-base + libobjc2 + performance
        self.requires("gnustep-base/1.31.1", transitive_headers=True, transitive_libs=True)
        self.requires("performance/0.6.0", transitive_headers=True, transitive_libs=True)
        self.requires("libobjc2/2.2.1", transitive_headers=True, transitive_libs=True)
        # 数据库后端 bundle（MySQL/Postgres/SQLite 制品仓依赖齐备，全部保留）
        self.requires("mysql/8.0.46", transitive_headers=True, transitive_libs=True)
        self.requires("libpq/18.6", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.53.4", transitive_headers=True, transitive_libs=True)
        # 版本冲突仲裁：curl 依赖 openssl/3.5.6.1，mysql 依赖 openssl/3.5.6.1.1
        # mysql 配方按 3.5.6.1.1 构建，统一到该版本避免 graph 冲突。
        self.requires("openssl/3.5.6.1.1", override=True)
        # zlib 冲突仲裁：mysql 依赖 zlib/1.3.1，图内已有 zlib/1.3.1.1，统一到更新版本。
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        self.tool_requires("gnustep-make/2.9.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    # ---- helpers ---------------------------------------------------------

    def _gnustep_make_folder(self):
        return self.dependencies.build["gnustep-make"].package_folder

    def _prepare_gnustep_make_scripts(self):
        """把 gnustep-make 包的 bin/Makefiles 复制到本包可写目录并修复 shebang。"""
        make_folder = self._gnustep_make_folder()
        local_bin = os.path.join(self.build_folder, "gnustep-bin")
        local_mk = os.path.join(self.build_folder, "gnustep-makefiles")
        os.makedirs(local_bin, exist_ok=True)
        src_bin = os.path.join(make_folder, "bin")
        if os.path.isdir(src_bin):
            shutil.copytree(src_bin, local_bin, dirs_exist_ok=True)
        src_mk = os.path.join(make_folder, "share", "GNUstep", "Makefiles")
        if os.path.isdir(src_mk):
            shutil.copytree(src_mk, local_mk, dirs_exist_ok=True)
        for root in (local_bin, local_mk):
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    self._prepare_shell_script(os.path.join(dirpath, filename))
        self._local_gnustep_bin = local_bin
        self._local_gnustep_makefiles = local_mk
        self._provide_plmerge(local_bin)

    def _provide_plmerge(self, bin_dir):
        """提供 plmerge 兼容工具（OpenStep plist 文本合并）。

        GNUstep bundle 构建时用 plmerge 合并 xxxInfo.plist；gnustep-make 包
        未携带该工具，故以 Python 实现相同语义。
        """
        script = os.path.join(bin_dir, "plmerge")
        with open(script, "w") as fh:
            fh.write('''#!/usr/bin/env python3
"""Minimal plmerge replacement for GNUstep bundle/framework plist merging."""
import sys


def _read_body(path):
    with open(path, "r") as fh:
        text = fh.read().strip()
    if text.startswith("{"):
        text = text[1:]
    idx = text.rfind("}")
    if idx != -1:
        text = text[:idx]
    return text.strip()


def main(argv):
    if not argv:
        sys.exit(1)
    target = argv[0]
    sources = argv[1:]
    parts = [_read_body(target)]
    for src in sources:
        parts.append(_read_body(src))
    with open(target, "w") as fh:
        fh.write("{\\n" + "\\n".join(parts) + "\\n}\\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
''')
        os.chmod(script, 0o755)

    def _gnustep_environment(self):
        local_bin = getattr(self, "_local_gnustep_bin", None) or os.path.join(
            self._gnustep_make_folder(), "bin")
        local_mk = getattr(self, "_local_gnustep_makefiles", None) or os.path.join(
            self._gnustep_make_folder(), "share", "GNUstep", "Makefiles")
        environment = Environment()
        environment.prepend_path("PATH", local_bin)
        environment.define_path("GNUSTEP_MAKEFILES", local_mk)
        environment.define("GNUSTEP_INSTALLATION_DOMAIN", "SYSTEM")
        environment.define("OBJC_RUNTIME_LIB", "gnu")
        return environment

    def _env_prefix(self):
        parts = ["env",
                 "-u", "GNUSTEP_USER_DIR",
                 "-u", "GNUSTEP_FLATTENED",
                 "-u", "GNUSTEP_SYSTEM_ROOT",
                 "-u", "LD_LIBRARY_PATH",
                 "-u", "LIBS",
                 "-u", "CPPFLAGS", "-u", "CFLAGS",
                 "-u", "CXXFLAGS", "-u", "LDFLAGS",
                 "-u", "PKG_CONFIG_PATH", "-u", "SHELL", "-u", "CONFIG_SHELL"]
        parts.append("OBJC_RUNTIME_LIB=gnu")
        local_bin = getattr(self, "_local_gnustep_bin", None)
        local_mk = getattr(self, "_local_gnustep_makefiles", None)
        if local_bin:
            parts.append(f'PATH="{local_bin}:$PATH"')
        if local_mk:
            parts.append(f'GNUSTEP_MAKEFILES="{local_mk}"')
        # configure 与 make 都需要 C/C++ 编译器（OHOS clang）；不再清除 CC/CXX
        cc = self._compiler_path()
        parts.append(f'CC="{cc}"')
        parts.append(f'CXX="{cc}"')
        # 依赖头/库路径注入（configure 探测与 make 链接共用）
        inc = " ".join(
            f"-I{self._path_of(dep, 'includedirs', 'include')}"
            for _n, dep in self.dependencies.items()
            if getattr(dep, "package_folder", None))
        lib = " ".join(
            f"-L{self._path_of(dep, 'libdirs', 'lib')}"
            for _n, dep in self.dependencies.items()
            if getattr(dep, "package_folder", None))
        parts.append(f'CPPFLAGS="{inc}"')
        parts.append(f'LDFLAGS="{lib}"')
        # MySQL 静态库为 C++ 编译（client.cc 引用 operator new/delete、basic_string），
        # 链接测试需 C++ 运行时 + SSL/zlib 传递依赖；否则 AC_CHECK_LIB(mysqlclient)
        # 失败 → MYSQL 恒为空 → MySQL.bundle 不构建
        parts.append('LIBS="-lc++ -lssl -lcrypto -lz"')
        parts.append(f'ADDITIONAL_INCLUDE_DIRS="{inc}"')
        parts.append(f'ADDITIONAL_LIB_DIRS="{lib}"')
        ld_dirs = []
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            ld_dirs.append(self._path_of(dep, "libdirs", "lib"))
        ld_dirs += list(_OHOS_SYSTEM_LIBDIRS)
        parts.append('LD_LIBRARY_PATH="%s"' % ":".join(ld_dirs))
        return " ".join(parts) + " "

    def _compiler_path(self):
        """返回可用 clang 路径（configure AC_PROG_CC 需要 CC 可执行）。"""
        cc = os.environ.get("CC")
        if cc:
            return cc
        cc = shutil.which("clang")
        if cc:
            return cc
        for candidate in ("/data/service/hnp/bin/clang", "/usr/bin/clang"):
            if os.path.exists(candidate):
                return candidate
        return "clang"

    def _path_of(self, dependency, cpp_attr, fallback):
        values = getattr(dependency.cpp_info, cpp_attr)
        if values:
            value = values[0]
            if os.path.isabs(value):
                return value
            return os.path.join(dependency.package_folder, value)
        return os.path.join(dependency.package_folder, fallback)

    @staticmethod
    def _resolve_shell(env_var):
        shell = os.environ.get(env_var)
        if shell:
            return shell
        for candidate in ("/data/service/hnp/bin/bash", "/bin/bash", "/bin/sh"):
            if os.path.exists(candidate):
                return candidate
        return "sh"

    @staticmethod
    def _script_shell():
        return SQLClientConan._resolve_shell("CONFIG_SHELL")

    @staticmethod
    def _script_shebang():
        return SQLClientConan._resolve_shell("GNUSTEP_SCRIPT_SHELL")

    @staticmethod
    def _ensure_executable(path):
        if not os.path.isfile(path):
            return
        try:
            os.chmod(path, 0o755)
        except OSError:
            try:
                mode = os.stat(path).st_mode
                os.chmod(path, mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
                         | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                pass

    def _prepare_shell_script(self, path):
        if not os.path.isfile(path):
            return
        try:
            with open(path, "rb") as script:
                lines = script.read().splitlines(keepends=True)
        except OSError:
            return
        if not lines or not lines[0].startswith(b"#!"):
            return
        first_line = lines[0].decode("utf-8", "ignore").strip()
        for prefix in ("#!/bin/sh", "#! /bin/sh"):
            if first_line == prefix or first_line.startswith(prefix + " "):
                suffix = first_line[len(prefix):]
                lines[0] = f"#!{self._script_shebang()}{suffix}\n".encode("utf-8")
                with open(path, "wb") as script:
                    script.writelines(lines)
                break
        self._ensure_executable(path)

    def _prepare_gnustep_scripts(self):
        script_names = {
            "config.guess", "config.sub", "configure", "depcomp",
            "install-sh", "missing", "mkinstalldirs",
        }
        for root in dict.fromkeys((self.source_folder,)):
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    if filename in script_names:
                        self._prepare_shell_script(os.path.join(dirpath, filename))

    # ---- build steps -----------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        self._prepare_gnustep_make_scripts()
        self._prepare_gnustep_scripts()
        prefix = self._env_prefix()
        with self._gnustep_environment().vars(self).apply():
            with chdir(self, self.source_folder):
                # configure：保留 MySQL/Postgres/SQLite 后端，关闭制品仓无依赖库的 ECPG/JDBC
                configure_cmd = (
                    f'{prefix}./configure '
                    f'--disable-ecpg-bundle --disable-jdbc-bundle '
                    f'--with-gnustep-include-dir={self._path_of(self.dependencies["gnustep-base"], "includedirs", "Library/Headers")} '
                    f'--with-gnustep-lib-dir={self._path_of(self.dependencies["gnustep-base"], "libdirs", "Library/Libraries")} '
                    f'--without-java '
                    f'--without-oracle'
                )
                self.run(configure_cmd, ignore_errors=True)
                # make 构建（LN_S=true 规避 hmdfs ln 限制；两阶段: 首次含后端 bundle 可能因
                # 产物布局缺失失败，补建后重跑）
                self.run(f'{prefix}make -j1 '
                         f'shared={"yes" if self.options.shared else "no"} debug=no '
                         f'messages=yes GNUSTEP_INSTALLATION_DOMAIN=SYSTEM '
                         f'MKDIRS="mkdir -p" LN_S="true" '
                         f'AUXILIARY_TOOL_LIBS="-lgnustep-base -lPerformance"',
                         ignore_errors=True)
                # 为 obj 目录补 libSQLClient.so soname 别名（LN_S=true 未建符号链接，
                # bundle 的 LIB_DIRS=-L./obj 需 -lSQLClient 可解析）
                self._fix_obj_aliases()
                self.run(f'{prefix}make -j1 '
                         f'shared={"yes" if self.options.shared else "no"} debug=no '
                         f'messages=yes GNUSTEP_INSTALLATION_DOMAIN=SYSTEM '
                         f'MKDIRS="mkdir -p" LN_S="true" '
                         f'AUXILIARY_TOOL_LIBS="-lgnustep-base -lPerformance"')

    def _fix_obj_aliases(self):
        """为 obj 目录补 libSQLClient.so 别名（hmdfs 不便建符号链接，用 copyfile）。"""
        obj_dir = os.path.join(self.source_folder, "obj")
        if not os.path.isdir(obj_dir):
            return
        versioned = os.path.join(obj_dir, "libSQLClient.so.1.9.0")
        if not os.path.isfile(versioned):
            return
        for name in ("libSQLClient.so.1.9", "libSQLClient.so.1", "libSQLClient.so"):
            dst = os.path.join(obj_dir, name)
            if not os.path.exists(dst):
                shutil.copy2(versioned, dst)
        self.output.info("sqlclient obj soname aliases created")

    def package(self):
        # 头文件（SQLClient.h 安装于 Library/Headers/SQLClient/）
        copy(
            self,
            "SQLClient.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "Library", "Headers", "SQLClient"),
            keep_path=False,
        )
        # 核心库 libSQLClient.so*（含 soname 别名，hmdfs ln 受限用 copyfile）
        obj_dir = os.path.join(self.source_folder, "obj")
        if os.path.isdir(obj_dir):
            for fn in os.listdir(obj_dir):
                if fn.startswith("libSQLClient"):
                    copy(
                        self,
                        fn,
                        src=obj_dir,
                        dst=os.path.join(self.package_folder, "Library", "Libraries"),
                        keep_path=False,
                    )
        lib_dst = os.path.join(self.package_folder, "Library", "Libraries")
        versioned = os.path.join(lib_dst, "libSQLClient.so.1.9.0")
        if os.path.isfile(versioned):
            # SONAME = libSQLClient.so.1.9 (INTERFACE_VERSION=1.9)，运行时加载器按 SONAME 查找
            for name in ("libSQLClient.so.1.9", "libSQLClient.so.1", "libSQLClient.so"):
                dst = os.path.join(lib_dst, name)
                if not os.path.exists(dst):
                    shutil.copy2(versioned, dst)
            self.output.info("sqlclient soname aliases created")
        # bundle 模块（MySQL/Postgres/SQLite.bundle，位于 Library/Bundles/SQLClient1.9/）
        for root, dirs, files in os.walk(self.source_folder):
            if root.endswith(".bundle"):
                rel = os.path.relpath(root, self.source_folder)
                target = os.path.join(self.package_folder, "Library", "Bundles", "SQLClient1.9", rel)
                os.makedirs(target, exist_ok=True)
                for fn in files:
                    shutil.copy2(os.path.join(root, fn), os.path.join(target, fn))
        # 许可
        for license_file in ("COPYING.LIB", "COPYING"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.includedirs = ["Library/Headers"]
        self.cpp_info.libdirs = ["Library/Libraries"]
        self.cpp_info.libs = ["SQLClient"]
        self.cpp_info.requires = [
            "gnustep-base::gnustep-base",
            "performance::performance",
            "libobjc2::libobjc2",
            "mysql::mysql",
            "libpq::libpq",
            "sqlite3::sqlite3",
        ]
        objc_flags = [
            "-fobjc-runtime=gcc",
            "-fblocks",
            "-fconstant-string-class=NSConstantString",
        ]
        self.cpp_info.cflags = objc_flags
        self.cpp_info.cxxflags = objc_flags
        self.cpp_info.exelinkflags = ["-fobjc-runtime=gcc", "-fblocks"]
        self.cpp_info.sharedlinkflags = ["-fobjc-runtime=gcc", "-fblocks"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.set_property("cmake_file_name", "sqlclient")
        self.cpp_info.set_property("cmake_target_name", "sqlclient::sqlclient")
        self.cpp_info.set_property("pkg_config_name", "sqlclient")

        root = self.package_folder
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries"))
        self.buildenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)
        self.runenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)