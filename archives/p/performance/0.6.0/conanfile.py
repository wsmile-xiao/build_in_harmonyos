#!/usr/bin/env python3
"""Conan recipe for GNUstep Performance 0.6.0 (libPerformance)."""

import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    chdir,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout

# OHOS 系统运行库目录（本平台硬编码，来源: OHOS NDK 默认安装布局）。
_OHOS_SYSTEM_LIBDIRS = (
    "/system/lib64",
    "/system/lib64/ndk",
    "/data/storage/el1/bundle/libs/arm64",
)


class PerformanceConan(ConanFile):
    name = "performance"
    version = "0.6.0"
    description = "GNUstep Performance library (caches, FIFO, tickers, thread pools)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnustep.github.io/"
    url = "https://github.com/gnustep/libs-performance"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"performance is prepared for Linux/OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Performance 仅依赖 Foundation (gnustep-base) 与 ObjC runtime
        self.requires("gnustep-base/1.31.1", transitive_headers=True, transitive_libs=True)
        self.requires("libobjc2/2.2.1", transitive_headers=True, transitive_libs=True)

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
                 "-u", "CC", "-u", "CXX", "-u", "CPPFLAGS", "-u", "CFLAGS",
                 "-u", "CXXFLAGS", "-u", "LDFLAGS",
                 "-u", "PKG_CONFIG_PATH", "-u", "SHELL", "-u", "CONFIG_SHELL"]
        parts.append("OBJC_RUNTIME_LIB=gnu")
        local_bin = getattr(self, "_local_gnustep_bin", None)
        local_mk = getattr(self, "_local_gnustep_makefiles", None)
        if local_bin:
            parts.append(f'PATH="{local_bin}:$PATH"')
        if local_mk:
            parts.append(f'GNUSTEP_MAKEFILES="{local_mk}"')
        # 依赖头/库路径: 通过 GNUstep make 的 ADDITIONAL_INCLUDE_DIRS /
        # ADDITIONAL_LIB_DIRS 注入 (gnustep-make 2.9.2.1 原生支持,
        # 纯 make 构建无 configure, 无法像 gnustep-base/gui 那样经 configure
        # 固化路径, 必须在 make 命令行显式给出)
        inc = " ".join(
            f"-I{self._path_of(dep, 'includedirs', 'include')}"
            for _n, dep in self.dependencies.items()
            if getattr(dep, "package_folder", None))
        lib = " ".join(
            f"-L{self._path_of(dep, 'libdirs', 'lib')}"
            for _n, dep in self.dependencies.items()
            if getattr(dep, "package_folder", None))
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
        return PerformanceConan._resolve_shell("CONFIG_SHELL")

    @staticmethod
    def _script_shebang():
        return PerformanceConan._resolve_shell("GNUSTEP_SCRIPT_SHELL")

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

    def _link_performance_library(self):
        """手动生成主库及 .so/.so.0/.so.0.6 别名（hmdfs 上 ln -s 受限，用 copyfile）。

        GNUstep make 以 INTERFACE_VERSION=0.6 生成 soname libPerformance.so.0.6，
        链接期记录该 soname，运行期必须存在对应文件；补全全部别名。
        """
        obj_dir = os.path.join(self.source_folder, "obj")
        candidates = (
            os.path.join(obj_dir, "libPerformance.so.0.6.0"),
            os.path.join(obj_dir, "libPerformance.so.0.6"),
        )
        primary = next((p for p in candidates if os.path.isfile(p)), None)
        if primary is None:
            raise ConanException(
                f"libPerformance.so not produced by make; build/link failed: "
                f"{[f for f in os.listdir(obj_dir) if f.startswith('libPerformance')] if os.path.isdir(obj_dir) else 'no obj dir'}")
        for alias in ("libPerformance.so.0.6", "libPerformance.so.0",
                      "libPerformance.so"):
            alias_path = os.path.join(obj_dir, alias)
            if os.path.lexists(alias_path):
                os.unlink(alias_path)
            shutil.copyfile(primary, alias_path)

    # ---- build steps -----------------------------------------------------

    def build(self):
        self._prepare_gnustep_make_scripts()
        self._prepare_gnustep_scripts()
        prefix = self._env_prefix()
        with self._gnustep_environment().vars(self).apply():
            with chdir(self, self.source_folder):
                # 预创建 obj 目录消除 hmdfs 首次 mkdir 竞态
                self.run(f'{prefix}mkdir -p obj')
                self.run(f'{prefix}make -j1 '
                         f'shared={"yes" if self.options.shared else "no"} debug=no '
                         f'messages=yes GNUSTEP_INSTALLATION_DOMAIN=SYSTEM '
                         f'MKDIRS="mkdir -p" LN_S="true"',
                         ignore_errors=True)
                self._link_performance_library()

    def package(self):
        # 头文件放入 Library/Headers/Performance/ 子目录:
        # GNUstep 生态以 <Performance/GSCache.h> 引用（SQLClient 等下游如此
        # #import），必须保持子目录布局而非平铺到 Headers 根。
        copy(
            self,
            "*.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "Library", "Headers", "Performance"),
            keep_path=False,
        )
        # 主库产物
        copy(
            self,
            "libPerformance.so*",
            src=os.path.join(self.source_folder, "obj"),
            dst=os.path.join(self.package_folder, "Library", "Libraries"),
            keep_path=False,
        )
        for license_file in ("COPYING", "COPYING.LIB"):
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
        self.cpp_info.libs = ["Performance"]
        self.cpp_info.requires = [
            "gnustep-base::gnustep-base",
            "libobjc2::libobjc2",
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
        self.cpp_info.set_property("cmake_file_name", "performance")
        self.cpp_info.set_property("cmake_target_name", "performance::performance")
        self.cpp_info.set_property("pkg_config_name", "performance")

        root = self.package_folder
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries"))
        self.buildenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)
        self.runenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)