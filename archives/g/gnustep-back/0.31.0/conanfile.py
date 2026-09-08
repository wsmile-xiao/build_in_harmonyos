#!/usr/bin/env python3
"""Conan recipe for GNUstep Back 0.31.0 (libgnustep-back, headless backend)."""

import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# OHOS 系统运行库目录（本平台硬编码，来源: OHOS NDK 默认安装布局）。
_OHOS_SYSTEM_LIBDIRS = (
    "/system/lib64",
    "/system/lib64/ndk",
    "/data/storage/el1/bundle/libs/arm64",
)


class GnustepBackConan(ConanFile):
    name = "gnustep-back"
    version = "0.31.0"
    description = "GNUstep backend library (headless backend for AppKit)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnustep.github.io/"
    url = "https://github.com/gnustep/libs-back"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gnustep-back is prepared for Linux/OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gnustep-back 编译依赖 AppKit/Foundation 头（来自 gnustep-gui/gnustep-base）
        self.requires("gnustep-gui/0.31.1", transitive_headers=True, transitive_libs=True)
        self.requires("gnustep-base/1.31.1", transitive_headers=True, transitive_libs=True)
        self.requires("libobjc2/2.2.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("gnustep-make/2.9.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    # ---- helpers ---------------------------------------------------------

    def _path_of(self, dependency, cpp_attr, fallback):
        values = getattr(dependency.cpp_info, cpp_attr)
        if values:
            value = values[0]
            if os.path.isabs(value):
                return value
            return os.path.join(dependency.package_folder, value)
        return os.path.join(dependency.package_folder, fallback)

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

    def _build_sysroot(self):
        """构造合并 GNUstep 系统根目录。

        gnustep-back 的 configure 不识别 --with-include-flags/--with-library-flags
        （那是 gnustep-gui 自定义参数）；它通过
        GNUSTEP_SYSTEM_ROOT/Library/{Headers,Libraries} 解析依赖头与库。
        因此把 gnustep-base/gnustep-gui 的 Headers/Libraries 合并复制到
        build_folder/sysroot/Library/ 下，构造唯一的 GNUstep 系统根。
        """
        sysroot = os.path.join(self.build_folder, "sysroot")
        lib_root = os.path.join(sysroot, "Library")
        os.makedirs(os.path.join(lib_root, "Headers"), exist_ok=True)
        os.makedirs(os.path.join(lib_root, "Libraries"), exist_ok=True)
        for dep_name in ("gnustep-base", "gnustep-gui"):
            dep = self.dependencies[dep_name]
            if not getattr(dep, "package_folder", None):
                continue
            hdr = dep.package_folder + "/Library/Headers"
            if os.path.isdir(hdr):
                shutil.copytree(
                    hdr, os.path.join(lib_root, "Headers"),
                    dirs_exist_ok=True)
            lib = dep.package_folder + "/Library/Libraries"
            if os.path.isdir(lib):
                shutil.copytree(
                    lib, os.path.join(lib_root, "Libraries"),
                    dirs_exist_ok=True)
        # libobjc2 头/库
        try:
            objc = self.dependencies["libobjc2"]
        except (KeyError, TypeError):
            objc = None
        if objc is not None and getattr(objc, "package_folder", None):
            shutil.copytree(
                objc.package_folder + "/include",
                os.path.join(lib_root, "Headers"),
                dirs_exist_ok=True)
            shutil.copytree(
                objc.package_folder + "/lib",
                os.path.join(lib_root, "Libraries"),
                dirs_exist_ok=True)
        self._local_sysroot = sysroot

    def _gnustep_environment(self):
        local_bin = getattr(self, "_local_gnustep_bin", None) or os.path.join(
            self._gnustep_make_folder(), "bin")
        local_mk = getattr(self, "_local_gnustep_makefiles", None) or os.path.join(
            self._gnustep_make_folder(), "share", "GNUstep", "Makefiles")
        sysroot = getattr(self, "_local_sysroot", None)
        environment = Environment()
        environment.prepend_path("PATH", local_bin)
        environment.define_path("GNUSTEP_MAKEFILES", local_mk)
        environment.define("GNUSTEP_INSTALLATION_DOMAIN", "SYSTEM")
        environment.define("OBJC_RUNTIME_LIB", "gnu")
        if sysroot:
            environment.define("GNUSTEP_SYSTEM_HEADERS",
                               os.path.join(sysroot, "Library", "Headers"))
            environment.define("GNUSTEP_SYSTEM_LIBRARIES",
                               os.path.join(sysroot, "Library", "Libraries"))
            environment.define("GNUSTEP_SYSTEM_ROOT", sysroot)
        return environment

    def _env_prefix(self, clean_compile_vars=False):
        parts = ["env",
                 "-u", "GNUSTEP_USER_DIR",
                 "-u", "GNUSTEP_FLATTENED",
                 "-u", "LD_LIBRARY_PATH",
                 # GNUSTEP_SYSTEM_ROOT 环境注入在 gnustep-make 2.9.2.1 已废弃
                 # (common.make: "GNUSTEP_SYSTEM_ROOT is obsolete"):
                 # 依赖头/库查找路径由 configure 期间经 GNUstep.sh 推导并固化进
                 # config.make/back.make, make 阶段不再需要该环境变量。
                 "-u", "GNUSTEP_SYSTEM_ROOT",
                 # LIBS 由 AutotoolsDeps 注入, 含 -lgnustep-gui; 空 conftest
                 # 链接时会加载 libgnustep-gui.so, 其引用 __objc_class_name_GSBackend
                 # (本库提供, 尚未构建) 被 lld --no-allow-shlib-undefined 拒绝。
                 # gnustep-back configure 的依赖检测走 PKG_CHECK_MODULES/
                 # AC_CHECK_LIB 显式进行, 无需预注入依赖链接库, 故统一清理。
                 "-u", "LIBS"]
        if clean_compile_vars:
            parts.extend([
                "-u", "CC", "-u", "CXX", "-u", "CPPFLAGS", "-u", "CFLAGS",
                "-u", "CXXFLAGS", "-u", "LDFLAGS",
                "-u", "PKG_CONFIG_PATH", "-u", "SHELL", "-u", "CONFIG_SHELL",
            ])
        parts.append("OBJC_RUNTIME_LIB=gnu")
        local_bin = getattr(self, "_local_gnustep_bin", None)
        local_mk = getattr(self, "_local_gnustep_makefiles", None)
        if local_bin:
            parts.append(f'PATH="{local_bin}:$PATH"')
        if local_mk:
            parts.append(f'GNUSTEP_MAKEFILES="{local_mk}"')
        sysroot = getattr(self, "_local_sysroot", None)
        # make 阶段不再注入 GNUSTEP_SYSTEM_ROOT: gnustep-make 2.9.2.1 已废弃该
        # 环境变量(common.make obsolete 检查); 依赖头/库路径由 configure 经
        # GNUstep.sh 与 GNUSTEP_SYSTEM_HEADERS/LIBRARIES 固化, 无需回填 ROOT。
        ld_dirs = [os.path.join(sysroot, "Library", "Libraries")] if sysroot else []
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            ld_dirs.append(self._path_of(dep, "libdirs", "lib"))
        ld_dirs += list(_OHOS_SYSTEM_LIBDIRS)
        parts.append('LD_LIBRARY_PATH="%s"' % ":".join(ld_dirs))
        return " ".join(parts) + " "

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
        return GnustepBackConan._resolve_shell("CONFIG_SHELL")

    @staticmethod
    def _script_shebang():
        return GnustepBackConan._resolve_shell("GNUSTEP_SCRIPT_SHELL")

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

    def _prepare_configure_scripts(self):
        script_names = {
            "config.guess", "config.sub", "configure", "depcomp",
            "install-sh", "missing", "mkinstalldirs",
        }
        for root in dict.fromkeys((self.source_folder,)):
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    if filename in script_names:
                        self._prepare_shell_script(os.path.join(dirpath, filename))

    def _patch_autoconf_tmp_umask(self):
        if str(self.settings.os) != "OHOS":
            return
        configure_script = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, configure_script, "umask 077 && mktemp -d",
            "umask 022 && mktemp -d", strict=False)
        replace_in_file(
            self, configure_script, "umask 077 && mkdir",
            "umask 022 && mkdir", strict=False)

    def _link_back_library(self):
        """手动生成主库及 .so/.so.0 别名（hmdfs 上 ln -s 受限，用 copyfile）。"""
        obj_dir = os.path.join(self.source_folder, "Source", "obj")
        primary = os.path.join(obj_dir, "libgnustep-back.so.0.31.0")
        if not os.path.isfile(primary):
            raise ConanException(
                f"libgnustep-back.so.0.31.0 missing after make: {primary}")
        for alias in ("libgnustep-back.so.0", "libgnustep-back.so"):
            alias_path = os.path.join(obj_dir, alias)
            if os.path.lexists(alias_path):
                os.unlink(alias_path)
            shutil.copyfile(primary, alias_path)

    # ---- build steps -----------------------------------------------------

    def generate(self):
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # OHOS 无 X11: 强制 headless 后端（零外部图形依赖）
        # --without-freetype: configure.ac 中 freetype 用 PKG_CHECK_MODULES 无
        # fallback 且默认启用, 但 headless 后端不渲染字体(仅枚举), 无需 freetype;
        # fontconfig/cairo 等检测自带 fallback(--enable-graphics=headless 分支
        # "Nothing to do"), 不受影响。
        tc.configure_args.extend([
            "--enable-server=headless",
            "--enable-graphics=headless",
            "--without-freetype",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_gnustep_make_scripts()
        self._build_sysroot()
        self._prepare_configure_scripts()
        self._patch_autoconf_tmp_umask()
        autotools = Autotools(self)
        with self._gnustep_environment().vars(self).apply():
            with chdir(self, self.source_folder):
                configure_script = os.path.join(self.source_folder, "configure")
                prefix_cfg = self._env_prefix(clean_compile_vars=False)
                self.run(
                    f'{prefix_cfg}"{self._script_shell()}" "{configure_script}" '
                    f'{autotools._configure_args}'
                )
            with chdir(self, os.path.join(self.source_folder, "Source")):
                prefix_make = self._env_prefix(clean_compile_vars=True)
                self.run(f'{prefix_make}mkdir -p obj/libgnustep-back.obj')
                self.run(f'{prefix_make}make -j1 '
                         f'shared={"yes" if self.options.shared else "no"} debug=no '
                         f'messages=yes GNUSTEP_INSTALLATION_DOMAIN=SYSTEM '
                         # BACKEND_BUNDLE 置空: 强行走 library.make 分支产出普通
                         # 共享库 libgnustep-back.so（bundle 打包需 plmerge 工具,
                         # 本机/制品仓均无; 后端由应用侧链接, 参考 gnustep-gui 的
                         # gsbackend_stub 思路, 不依赖 bundle 加载机制）
                         f'BACKEND_BUNDLE= '
                         f'MKDIRS="mkdir -p" '
                         f'LN_S="true"',
                         ignore_errors=True)
                primary = os.path.join(
                    self.source_folder, "Source", "obj",
                    "libgnustep-back.so.0.31.0")
                if not os.path.isfile(primary):
                    raise ConanException(
                        "libgnustep-back.so.0.31.0 not produced by make; "
                        "build/link failed (see full log)")
                self._link_back_library()
        if can_run(self):
            self.output.info(
                "Upstream backend tests are built by GNUmakefile; "
                "execution is covered by test_package (AppKit consumer).")
        else:
            self.output.info(
                "cross-building: upstream GNUstep backend tests are not "
                "executed on the build host")

    def package(self):
        # 公共头（backend 使用 AppKit/Foundation 头, 自身头极少, 一并携带）
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "Headers"),
            dst=os.path.join(self.package_folder, "Library", "Headers"),
        )
        copy(
            self,
            "libgnustep-back.so*",
            src=os.path.join(self.source_folder, "Source", "obj"),
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
        self.cpp_info.libs = ["gnustep-back"]
        self.cpp_info.requires = [
            "gnustep-gui::gnustep-gui",
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
        self.cpp_info.set_property("cmake_file_name", "gnustep-back")
        self.cpp_info.set_property("cmake_target_name", "gnustep-back::gnustep-back")
        self.cpp_info.set_property("pkg_config_name", "gnustep-back")

        root = self.package_folder
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries"))
        self.buildenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)
        self.runenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)