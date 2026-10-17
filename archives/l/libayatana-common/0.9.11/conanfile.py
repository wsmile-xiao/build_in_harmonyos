#!/usr/bin/env python3
"""Conan recipe — libayatana-common 0.9.11 (Ayatana indicators common library).

libayatana-common 提供 Ayatana 指示器框架（indicator/desktop 子系统）的公共
基础设施：版本化符号、类型转换（GList<->std::vector）、单例/进程定位、安全
转义等 C/C++ 工具。CMake 构建，硬依赖 glib-2.0 ≥ 2.36 / gio-2.0 ≥ 2.36
（ohpcd 已发布 glib/2.84.0）。

可选特性（LOMIRI / GObjectIntrospection / Vala / Tests）默认 OFF 关闭——
OHOS 无 Lomiri 运行时、无 gobject-introspection 工具链，且上游测试依赖
glib 测试框架环境。

OHOS 适配（沿用 dconf/polkit 的 meson 依赖注入模式）：
- 私有 .pc 复制 + prefix 改写 + PKG_CONFIG_PATH 注入全部依赖包；
- PkgConfigDeps 生成 .pc + CMakeToolchain 传依赖路径。
"""
import os
import re as _re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps


def _fix_pc_prefix(pc_path, prefix):
    if not os.path.isfile(pc_path):
        return
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    data = _re.sub(r"(?m)^(libdir|static_libdir|includedir)=/usr/lib$",
                   rf"\1={os.path.join(prefix, 'lib')}", data)
    data = _re.sub(r"(?m)^(includedir)=/usr/include$",
                   rf"\1={os.path.join(prefix, 'include')}", data)
    open(pc_path, "w", encoding="utf-8").write(data)


class LibAyatanaCommonConan(ConanFile):
    name = "libayatana-common"
    version = "0.9.11"
    package_type = "library"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/AyatanaIndicators/libayatana-common"
    description = "libayatana-common — Ayatana indicators common infrastructure (C/C++)"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libayatana-common does not support os={self.settings.os}")

    def requirements(self):
        # utils.h 直接包含 glib.h / glib-object.h / gio/gio.h，需透传头文件与库
        # （借鉴 0.9.13 适配技术）。用 glib/2.88.0.1 与 0.9.13 对齐——该版本
        # 的 CMakeDeps 提供 glib-2.0/gobject-2.0/gio-2.0 组件（cpp_info.requires
        # 引用），glib/2.84.0 无这些组件名会导致 test_package 报
        # "Component 'glib::glib-2.0' not found"。
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # rule 4 整改：上游 tests/ 用 gtest/gmock（header-only，OHOS 可实跑）。
        # 用 test_requires 声明（仅测试编译运行用，非库运行时依赖——否则
        # package_info() 报 "direct dependency 'gmock' is not used by any
        # (cpp_info/components).requires"）。
        self.test_requires("gtest/1.17.0")
        self.test_requires("gmock/1.17.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static —— 显式按 shared 选项
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS: 无 GSettings/Intltool CMake 模块，SKIP_DATA_PO=ON 跳过 data/ po/
        # 子目录（0001 补丁增加该选项；借鉴 0.9.13）。
        tc.variables["SKIP_DATA_PO"] = "ON"
        tc.variables["ENABLE_TESTS"] = "ON"
        tc.variables["ENABLE_WERROR"] = "OFF"
        tc.variables["ENABLE_COVERAGE"] = "OFF"
        tc.variables["ENABLE_LOMIRI_FEATURES"] = "OFF"
        # gschemas.compiled 的 COMPILE_SCHEMA_EXECUTABLE：tests/CMakeLists.txt 用
        # pkg-config 查 glib_compile_schemas，但 build() 注入的 PKG_CONFIG_PATH 指向
        # glib 原始 pkgconfig（prefix=/ 未改写 → 返回 //bin/ 错误路径），而
        # generators_folder 的 .pc 由 PkgConfigDeps 生成（不含 glib_compile_schemas
        # 变量 → 返回空）——直接注入 glib 包 bin/glib-compile-schemas 绝对路径，
        # tests/CMakeLists.txt 补丁将优先使用该 CMake 变量。
        try:
            glib_pkg = self.dependencies["glib"].package_folder
            tc.variables["COMPILE_SCHEMA_EXECUTABLE"] = os.path.join(
                glib_pkg, "bin", "glib-compile-schemas")
        except Exception:
            pass
        # gtest/gmock 头路径：tests/CMakeLists.txt 的 DEPS_INCLUDE_DIRS 来自
        # pkg_check_modules(glib-2.0/gio-2.0)，不含 gtest/gmock——单独注入
        # include 变量，补丁 tst_utils 的 target_include_directories 引用。
        for dep_name, var_name in (("gtest", "GTEST_INCLUDE_DIR"),
                                   ("gmock", "GMOCK_INCLUDE_DIR")):
            try:
                dep_pkg = self.dependencies[dep_name].package_folder
                tc.variables[var_name] = os.path.join(dep_pkg, "include")
            except Exception:
                pass
        # gtest/gmock 库绝对路径：find_package(GMock) 在 conan PkgConfigDeps 下
        # 未设置 GTEST_LIBRARIES/GMOCK_LIBRARIES（tst_utils 链接报 undefined
        # symbol: testing::internal::MakeAndRegisterTestInfo）——注入 .a 绝对
        # 路径，补丁 tst_utils 的 target_link_libraries 引用。
        try:
            gt = self.dependencies["gtest"].package_folder
            tc.variables["GTEST_LIBRARIES"] = os.path.join(gt, "lib", "libgtest.a")
            tc.variables["GTEST_BOTH_LIBRARIES"] = ";".join([
                os.path.join(gt, "lib", "libgtest_main.a"),
                os.path.join(gt, "lib", "libgtest.a")])
        except Exception:
            pass
        try:
            gm = self.dependencies["gmock"].package_folder
            tc.variables["GMOCK_LIBRARIES"] = os.path.join(gm, "lib", "libgmock.a")
        except Exception:
            pass
        # g_libintl_*（glib gettext 重命名符号）由 glib 包自带 libintl.a 提供；
        # tst_utils 链接 libayatana-common.so 时需显式链接该 .a，否则
        # ld.lld 报 "--no-allow-shlib-undefined: g_libintl_bindtextdomain"。
        try:
            gl = self.dependencies["glib"].package_folder
            tc.variables["GLIB_INTL_LIBRARY"] = os.path.join(gl, "lib", "libintl.a")
        except Exception:
            pass
        tc.generate()
        # 依赖 .pc：复制**所有依赖包**（含 glib 的 Requires 链传递依赖 pcre2/
        # libffi 等）pkgconfig 目录的 .pc 到 generators_folder 并改写 prefix，
        # 保证 CMake 的 pkg_check_modules(DEPS glib-2.0/gio-2.0) 可解析。
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            src_pc = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(src_pc):
                continue
            for name in os.listdir(src_pc):
                if name.endswith(".pc"):
                    d = os.path.join(self.generators_folder, name)
                    if not os.path.exists(d):
                        shutil.copy2(os.path.join(src_pc, name), d)
                    _fix_pc_prefix(d, dep_pkg)

    def build(self):
        apply_conandata_patches(self)
        # PKG_CONFIG_PATH 注入 os.environ 保证 CMake 子进程解析 glib-2.0 等
        # 的 .pc（含 Requires 链 libffi/libpcre2）。
        pkgconfig_dirs = []
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if os.path.isdir(pc_dir) and pc_dir not in pkgconfig_dirs:
                pkgconfig_dirs.append(pc_dir)
        if pkgconfig_dirs:
            cur = os.environ.get("PKG_CONFIG_PATH", "")
            merged = [d for d in pkgconfig_dirs if d not in cur.split(os.pathsep)]
            if merged:
                os.environ["PKG_CONFIG_PATH"] = (os.pathsep.join(merged) +
                                                 (os.pathsep + cur if cur else ""))
            self.output.info("libayatana-common: PKG_CONFIG_PATH=%s"
                             % os.environ["PKG_CONFIG_PATH"])
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游测试（rule 4 实测回填）──
        # ENABLE_TESTS=OFF（默认）；若打开，上游测试用 glib 测试框架并依赖
        # 运行环境——OHOS 按 rule 1.2 平台限制声明（非跳过）。
        self.run("ctest -C {} --output-on-failure".format(self.build_folder),
                 env="conanbuild", ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ayatana-common"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # utils.h 包含 glib.h/glib-object.h/gio/gio.h，透传 glib 依赖
        # （借鉴 0.9.13 适配技术）。
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0",
                                  "glib::gio-2.0"]
