#!/usr/bin/env python3
"""Conan recipe — libayatana-appindicator-glib 2.0.3 (GLib-2.0 reimplementation).

Ayatana Application Indicators shared library. Provides:
  - lib/libayatana-appindicator-glib.so.2
  - lib/pkgconfig/ayatana-appindicator-glib.pc  (Requires: gio-2.0 gobject-2.0)
  - include/libayatana-appindicator-glib/ayatana-appindicator.h

注意：上游仓库是 libayatana-appindicator-glib（GLib-2.0 重实现，100% GTK-free /
dbusmenu-free），不是同名的 libayatana-appindicator（GTK/DBusMenu 旧实现，已废弃）。

HarmonyOS PC 适配说明：
  - 构建系统为 CMake，顶层 CMakeLists.txt 通过 pkg_check_modules(DEPS REQUIRED
    gio-2.0 gobject-2.0) 解析依赖（仅需 glib）。
  - GIR/typelib（gobject-introspection）、Vala bindings（vapigen）、docs
    （gi-docgen）在 OHOS 无对应工具 → 0001/0002 补丁新增 SKIP_INTROSPECTION
    选项跳过，仅交付 C 头文件 + 共享库 + .pc（消费方 ayatana-indicator-
    application 只用到 app_indicator_* API 与枚举，不依赖 GIR）。
  - glib 的 proxy-libintl 提供 g_libintl_* 符号，glib 系 .pc 未列 -lintl
    → 追加 -lintl（与 libayatana-common / gtk+ 配方 _augment_glib_pkg_config
    一致），否则 --no-allow-shlib-undefined 链接失败。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class LibayatanaappindicatorglibConan(ConanFile):
    name = "libayatana-appindicator-glib"
    version = "2.0.3"
    description = "Ayatana Application Indicators shared library (GLib-2.0 implementation)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/AyatanaIndicators/libayatana-appindicator-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        # gio-2.0 / gobject-2.0 由 glib 提供。必须与 application 依赖链统一：
        # gtk/3.24.43、libayatana-indicator/0.9.5、libdbusmenu 均用
        # glib/2.84.0.1，若此处用 2.88.0.1，application 图中会出现两个 glib
        # 版本，PkgConfigDeps 生成同名 .pc（glib-2.0.pc 等）互相覆盖。
        # 强制 glib 共享库：静态 glib 的 gobject-2.0.pc 会写死 -lffi（无对应
        # ffi.pc），且 pcre2 静态库不在链接 -L 路径上，导致
        # `unable to find library -lffi/-lpcre2-8/-lpcre2-posix`。共享 glib
        # 实例（glib/*:shared=True）与 gtk 链成功构建时一致。
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
            options={"shared": True},
        )

    def layout(self):
        cmake_layout(self)

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_url:
                raise
            self.output.warning(
                f"Primary source failed ({error}), trying mirror"
            )
            get(
                self,
                url=mirror_url,
                sha256=sources["sha256"],
                strip_root=True,
            )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS 无 gobject-introspection / vapigen / gi-docgen → 跳过 GIR、
        # Vala bindings 与 docs（0001/0002 补丁引入该选项）。
        toolchain.variables["SKIP_INTROSPECTION"] = "ON"
        # 测试套件依赖 gobject-introspection 生成的 typelib，一并关闭。
        toolchain.variables["ENABLE_TESTS"] = "OFF"
        toolchain.variables["ENABLE_WERROR"] = "OFF"
        # OHOS worker 的 /data/service/hnp/bin 下存在指向 glib_2.38.2 的
        # 软链接（glib-mkenums / glib-genmarshal），且目标缺失（断链）。
        # src/CMakeLists.txt 用 find_program() 搜索 PATH 会命中该断链，
        # 执行时报 `No such file or directory`。显式注入依赖 glib 包内的
        # 工具绝对路径（_build_environment 已将其 bin 加入 PATH，双保险）。
        self._set_glib_codegen_tools(toolchain)
        toolchain.generate()

    def _set_glib_codegen_tools(self, toolchain):
        """把 glib 代码生成工具（glib-mkenums / glib-genmarshal）显式注入
        CMake 变量，避免 find_program() 命中系统断链软链接。"""
        for var_name, tool_name in (
            ("GLIB_MKENUMS", "glib-mkenums"),
            ("GLIB_GENMARSHAL", "glib-genmarshal"),
        ):
            tool_path = None
            if "glib" in self.dependencies:
                candidate = os.path.join(
                    self.dependencies["glib"].package_folder, "bin", tool_name
                )
                if os.path.isfile(candidate):
                    tool_path = candidate
            if tool_path:
                toolchain.variables[var_name] = tool_path
            else:
                self.output.warning(
                    f"{tool_name} not found in glib package, "
                    "falling back to find_program() PATH search"
                )

    def _augment_glib_pkg_config(self):
        """glib 配方生成 glib-2.0.pc/gio-2.0.pc/gobject-2.0.pc 等，Libs 行未
        含 -lintl（glib 的 proxy-libintl 提供 g_libintl_* 符号）。追加
        -lintl（libdir 已在 -L 路径上），与 libayatana-common 配方一致。"""
        for pc_name in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            if re.search(r"^Libs:", content, flags=re.M):
                if "-lintl" in content:
                    continue
                content = re.sub(
                    r"^Libs:.*$",
                    lambda m: m.group(0) + " -lintl",
                    content,
                    count=1,
                    flags=re.M,
                )
            else:
                content += 'Libs: -L"${libdir}" -lintl\n'
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["ayatana-appindicator-glib"]
        # CMake install 把头文件装到 include/libayatana-appindicator-glib/，
        # includedirs 应指向 include/（test_package 以
        # <libayatana-appindicator-glib/ayatana-appindicator.h> 引用）。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "ayatana-appindicator-glib")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob_so(pattern))
        for target in targets:
            if os.path.islink(target) or os.path.isdir(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')


def glob_so(pattern):
    import glob as _glob

    return _glob.glob(pattern, recursive=True)
