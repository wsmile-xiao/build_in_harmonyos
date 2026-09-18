#!/usr/bin/env python3
"""Conan recipe — libopenrazer 0.4.0 (Qt wrapper around the D-Bus API from OpenRazer).

C++17 + meson 构建；产物：libopenrazer.so + 头文件 + pkg-config（libopenrazer.pc）。
依赖 Qt6（Core/DBus/Gui/Xml）—— 由 qtbase/6.11.1.2 提供。

关键适配点：
1. meson 的 qt6 模块通过 qmake6 定位 Qt6（QT6_QMAKE 环境变量指向 qtbase 的 qmake6），
   moc/rcc/uic 位于 qtbase 包的 bin/ 与 libexec/，需注入 PATH。
2. meson sanity check 二进制运行时需要 libc++_shared.so（/system/lib64）与
   qtbase 及其传递依赖动态库，LD_LIBRARY_PATH 必须显式注入（conan build 环境默认不含）。
3. 上游 translations 子目录依赖 lrelease（qtbase 制品仓不提供 LinguistTools），
   已通过 patches/0001-meson.build.patch 跳过；翻译文件仅影响界面本地化，不影响库核心功能。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class LibopenrazerConan(ConanFile):
    name = "libopenrazer"
    version = "0.4.0"
    description = "Qt wrapper around the D-Bus API from OpenRazer"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/z3ntu/libopenrazer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/DBus/Gui/Xml 模块均由 qtbase 提供；DBus 头文件需传递依赖
        self.requires("qtbase/6.11.1.2", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["demo"] = "false"
        tc.generate()

    def _build_env_prefix(self):
        """构造 meson 运行所需的显式环境前缀。

        - QT6_QMAKE / PATH：meson qt6 模块经 qmake6 定位 Qt6，moc/rcc/uic 在 qtbase libexec
        - CC/CXX/AR：CI worker 上 meson 无法从 PATH 定位 clang++（Unknown compiler），
          显式注入编译器路径（从 profile tools.build:compiler_executables 动态读取，
          account-utils/c-rbtree 同款先例）
        - LD_LIBRARY_PATH：sanity check 二进制与 qmake6 运行时需要 libc++_shared.so
          （/system/lib64）及各依赖库；lld 链接器依赖 libxml2.so.16，需动态探测
          OHOS SDK 的 llvm/lib 注入（E132，参照 qtbase 配方 _ohos_sdk_llvm_libdir）
        """
        qt_prefix = self.dependencies["qtbase"].package_folder.replace("\\", "/")
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir) and libdir not in lib_dirs:
                    lib_dirs.append(libdir)
        sys_lib = (
            "/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:"
            "/system/lib64:/system/lib64/ndk:/data/storage/el1/bundle/libs/arm64"
        )
        # lld 链接器运行时依赖 libxml2.so.16（OHOS SDK llvm/lib），
        # 不注入则 meson 探测 linker 失败（E132）。SDK 路径随编译器推导，
        # 不硬编码含版本号的绝对路径（W4 审计 P1）。
        sdk_llvm_lib = self._ohos_sdk_llvm_libdir()
        if sdk_llvm_lib and sdk_llvm_lib not in lib_dirs:
            lib_dirs.insert(0, sdk_llvm_lib)
        ld_path = ":".join(lib_dirs + [sys_lib])
        # 编译器路径动态读取（CI worker 无 /data/service/hnp/bin 在 PATH 中）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        cxx = compilers.get("cpp")
        compiler_env = ""
        if cc and cxx:
            compiler_env = f"CC={cc} CXX={cxx} "
        # meson 还需 llvm-ar 静态链接器（CI worker PATH 不含 /data/service/hnp/bin，
        # Unknown linker: llvm-ar，参照 account-utils/c-rbtree 先例显式注入）
        ar = compilers.get("archive")
        if not ar:
            # 从编译器路径推导 .../bin/clang -> .../bin/llvm-ar
            ar_bin = os.path.dirname(cc) if cc else "/data/service/hnp/bin"
            ar = os.path.join(ar_bin, "llvm-ar")
        compiler_env += f"AR={ar} "
        return (
            f"PATH={qt_prefix}/bin:{qt_prefix}/libexec:/data/service/hnp/bin:$PATH "
            f"{compiler_env}"
            f"QT6_QMAKE={qt_prefix}/bin/qmake6 "
            f"LD_LIBRARY_PATH={ld_path}"
        )

    def _ohos_sdk_llvm_libdir(self):
        """动态定位含 libxml2.so.16 的 OHOS SDK llvm/lib 目录。

        参照 qtbase 6.11.1.2 配方 _ohos_sdk_llvm_libdir：从活动编译器推导
        （-print-resource-dir → .../llvm/lib/clang/<ver> 的上级即 llvm/lib），
        回退到编译器路径 .../llvm/bin/clang++ → .../llvm/lib，并以
        libxml2.so.16 存在性校验。找不到返回 ""。
        """
        if str(self.settings.os) != "OHOS":
            return ""
        import subprocess as _subprocess

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            try:
                resource_dir = _subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=_subprocess.DEVNULL,
                    text=True,
                    timeout=30,
                ).strip()
                # resource_dir = .../llvm/lib/clang/15.0.4
                candidates.append(
                    os.path.dirname(os.path.dirname(resource_dir))
                )
            except (OSError, _subprocess.SubprocessError):
                pass
            # Fallback: .../llvm/bin/clang++ -> .../llvm/lib
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def build(self):
        apply_conandata_patches(self)
        env_prefix = self._build_env_prefix()
        self.run(
            env_prefix
            + f" meson setup {self.build_folder} {self.source_folder} "
            + "--buildtype=release -Ddemo=false --prefix=/",
            cwd=self.build_folder,
            env="conanbuild",
        )
        # compile 阶段 moc/rcc/uic 运行时同样需要 LD_LIBRARY_PATH
        # （libc++_shared.so 在 /system/lib64，qtbase lib 在依赖包）
        self.run(
            env_prefix + f" meson compile -C {self.build_folder} -j1",
            env="conanbuild",
        )

    def package(self):
        # meson install + DESTDIR=package_folder（--prefix=/ 已在上层 setup 指定）
        self.run(
            f"meson install -C {self.build_folder} --destdir {self.package_folder}",
            cwd=self.build_folder,
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.libs = ["openrazer"]
        self.cpp_info.set_property("pkg_config_name", "libopenrazer")
        # 注意：不通过 cpp_info.requires 引用 qtbase 组件——qtbase 采用
        # cmake_find_mode=none（自带 Qt6Config.cmake），CMakeDeps 不会为它生成
        # 配置文件；引用组件会使 libopenrazer-config.cmake 生成
        # find_dependency(qtbase) 而失败。消费者须自行 find_package(Qt6)
        # （参照 adwaita-qt/qca 先例）。
