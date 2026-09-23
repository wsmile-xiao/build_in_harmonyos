#!/usr/bin/env python3
"""Conan recipe for libdrumstick 2.10.0 on HarmonyOS PC.

libdrumstick 是 Qt 的 MIDI C++ 库，提供三个库：
  - libdrumstick-file   : SMF/RIFF/WRK MIDI 文件读写
  - libdrumstick-rt     : 实时 MIDI I/O（插件式后端：Network/FluidSynth/OSS）
  - libdrumstick-widgets: 钢琴键盘等 MIDI 控件

OHOS 适配要点（详见 notes.md）：
- Qt6 路线：qtbase(Core/Network/Gui/Widgets/Xml/Test) + qt5compat(Core5Compat)
  + qttools(LinguistTools/UiPlugin)；fluidsynth 提供 FluidSynth RT 后端。
- CMAKE_SYSTEM_NAME=OHOS：conan 的 OHOS toolchain 将系统映射为 HarmonyOS，
  而 CMake 4.1 没有 Platform/HarmonyOS.cmake（只有 OHOS.cmake，include Linux）。
  不显式设置会报 "System is unknown to cmake"，导致 1) 共享库不生成 SONAME；
  2) RT 插件 DT_NEEDED 写成相对路径 ../../../lib/...，运行时从 lib/drumstick2/
  解析错位 → rtTest 报 "There aren't input backends"。显式设置为 OHOS 后库
  生成 SONAME(libdrumstick-rt.so.2)、插件 DT_NEEDED 用 SONAME，上游 5 项测试
  全部通过。
- 关闭 OHOS 不可用后端：BUILD_ALSA(无 ALSA sequencer)、USE_SONIVOX、
  USE_PULSEAUDIO(与 SONIVOX 联动)、USE_PIPEWIRE；保留 USE_FLUIDSYNTH、
  USE_NETWORK。
- fluidsynth 包发布的 fluidsynth.pc 的 prefix 指向已清理的 build 目录，
  在 build 私有 prefix 下重写 prefix 后经 PKG_CONFIG_PATH 注入（R49）。
- Qt 工具（qmake/moc/lrelease）与测试二进制运行期需要 libc++_shared.so
  （OHOS SDK llvm lib）与 qtbase 动态库，configure/build/test 全程注入
  LD_LIBRARY_PATH（参考 E520）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LibdrumstickConan(ConanFile):
    name = "libdrumstick"
    version = "2.10.0"
    description = "MIDI C++ Libraries for Qt (file / rt / widgets)"
    license = "GPL-3.0-or-later"
    homepage = "https://drumstick.sourceforge.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdrumstick supports Linux and OHOS only"
            )

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        self.requires("qttools/6.11.1")
        self.requires("fluidsynth/2.5.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    _OHOS_SDK_LLVM_LIB = os.environ.get(
        "OHOS_SDK_LLVM_LIB",
        "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
    )

    def _fix_fluidsynth_pc(self):
        """fluidsynth 包发布的 fluidsynth.pc 的 prefix 指向已清理的 build
        目录；在 build 私有 prefix 下重写 prefix 供 PKG_CONFIG_PATH 使用。
        """
        fs_pkg = self.dependencies["fluidsynth"].package_folder
        src_pc = os.path.join(fs_pkg, "lib", "pkgconfig", "fluidsynth.pc")
        if not os.path.isfile(src_pc):
            return
        priv_pc_dir = os.path.join(self.build_folder, "priv-prefix", "lib", "pkgconfig")
        os.makedirs(priv_pc_dir, exist_ok=True)
        with open(src_pc, encoding="utf-8") as handle:
            content = handle.read()
        content = re.sub(r"^prefix=.*$", f"prefix={fs_pkg}", content, flags=re.M)
        with open(os.path.join(priv_pc_dir, "fluidsynth.pc"), "w", encoding="utf-8") as handle:
            handle.write(content)
        return priv_pc_dir

    def _sdk_libcxx_dirs(self):
        """OHOS SDK llvm 下含 libc++_shared.so 的目录（Qt 工具/测试运行期需要）。"""
        base = self._OHOS_SDK_LLVM_LIB
        return [
            os.path.join(base, "aarch64-linux-ohos"),
            os.path.join(base, "aarch64-linux-ohos", "c++"),
        ]

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 平台识别：OHOS → Platform/OHOS.cmake（include Linux）
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # Qt6 组件路径注入（qtbase 使用 cmake_find_mode=none，须显式指路）
        qtbase = self.dependencies["qtbase"].package_folder
        qt5compat = self.dependencies["qt5compat"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        fluidsynth = self.dependencies["fluidsynth"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
            p.replace("\\", "/")
            for p in (qtbase, qt5compat, qttools, fluidsynth)
        )
        tc.cache_variables["Qt6Core5Compat_DIR"] = os.path.join(
            qt5compat, "lib", "cmake", "Qt6Core5Compat"
        ).replace("\\", "/")
        tc.cache_variables["Qt6LinguistTools_DIR"] = os.path.join(
            qttools, "lib", "cmake", "Qt6LinguistTools"
        ).replace("\\", "/")
        # 功能开关
        tc.variables["BUILD_ALSA"] = "OFF"
        tc.variables["USE_SONIVOX"] = "OFF"
        tc.variables["USE_PULSEAUDIO"] = "OFF"
        tc.variables["USE_PIPEWIRE"] = "OFF"
        tc.variables["USE_FLUIDSYNTH"] = "ON"
        tc.variables["USE_NETWORK"] = "ON"
        tc.variables["BUILD_DOCS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        # 关键：跳过 CMake 的 RPATH 处理（CMAKE_SKIP_RPATH=TRUE）。
        # cmake.install() 默认会用 patchelf 清理/重写安装后库的 RPATH，
        # 这会破坏 OHOS 动态加载器所需的 ELF 结构（.rela 段被重排），
        # 导致安装后（conan package 内）的 libdrumstick-*.so 无法加载
        # （rtTest/test_package 报 "Error loading shared library"）。
        # 关闭后安装的库保持 build 产物原样，运行时依赖由
        # build()/test() 显式注入的 LD_LIBRARY_PATH 提供。
        tc.variables["CMAKE_SKIP_RPATH"] = "TRUE"
        tc.generate()
        pc_dir = self._fix_fluidsynth_pc()
        # configure/build 全程注入运行期库路径：qmake/moc/lrelease 与测试二进制
        # 需要 libc++_shared.so（SDK llvm）与 qtbase 动态库；fluidsynth.pc 走
        # PKG_CONFIG_PATH（E520 + R49 私有 prefix）。
        qtbase = self.dependencies["qtbase"].package_folder
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        for d in self._sdk_libcxx_dirs():
            self.buildenv_info.append_path("LD_LIBRARY_PATH", d)
        if pc_dir:
            self.buildenv_info.prepend_path("PKG_CONFIG_PATH", pc_dir)

    def _runtime_ld_paths(self):
        """configure/build/test 运行期需要的共享库搜索路径。

        注意：build_lib（本项目 build 树 lib）必须无条件保留——即使
        configure 之前该目录尚不存在，ctest 运行时它必然存在且测试
        二进制需要从其中加载 libdrumstick-*.so（SKIP_RPATH 后无
        build-tree RPATH 可依，只能靠 LD_LIBRARY_PATH）。
        """
        qtbase = self.dependencies["qtbase"].package_folder
        qt5compat = self.dependencies["qt5compat"].package_folder
        qttoo = self.dependencies["qttools"].package_folder
        fs = self.dependencies["fluidsynth"].package_folder
        build_lib = os.path.join(self.build_folder, "lib")
        paths = [
            build_lib,  # 始终保留（configure 前不存在也保留）
            os.path.join(qtbase, "lib"),
            os.path.join(qt5compat, "lib"),
            os.path.join(qttoo, "lib"),
            os.path.join(fs, "lib"),
            self._OHOS_SDK_LLVM_LIB,
            os.path.join(self._OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos"),
            os.path.join(self._OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos", "c++"),
        ]
        uniq = list(dict.fromkeys(paths))
        return [p for p in uniq if p == build_lib or os.path.isdir(p)]

    def _ld_value(self):
        return ":".join(self._runtime_ld_paths())

    def _env_part(self):
        """configure/build/test 的 cmake -E env 前缀（E520）。"""
        parts = ["LD_LIBRARY_PATH={}".format(self._ld_value())]
        pc_dir = os.path.join(self.build_folder, "priv-prefix", "lib", "pkgconfig")
        if os.path.isdir(pc_dir):
            parts.append("PKG_CONFIG_PATH={}".format(pc_dir))
        return " ".join(parts)

    def _configure_args(self):
        """手动 configure 的 -D 参数（与探索验证一致的完整参数集）。"""
        qtbase = self.dependencies["qtbase"].package_folder
        qt5compat = self.dependencies["qt5compat"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        fluidsynth = self.dependencies["fluidsynth"].package_folder
        prefix = ";".join(
            p.replace("\\", "/")
            for p in (qtbase, qt5compat, qttools, fluidsynth)
        )
        core5 = os.path.join(qt5compat, "lib", "cmake", "Qt6Core5Compat").replace("\\", "/")
        linguist = os.path.join(qttools, "lib", "cmake", "Qt6LinguistTools").replace("\\", "/")
        return (
            "-DCMAKE_SYSTEM_NAME=OHOS "
            '-DCMAKE_PREFIX_PATH="{prefix}" '
            '-DQt6Core5Compat_DIR="{core5}" '
            '-DQt6LinguistTools_DIR="{linguist}" '
            "-DBUILD_ALSA=OFF -DUSE_SONIVOX=OFF -DUSE_PULSEAUDIO=OFF "
            "-DUSE_PIPEWIRE=OFF -DUSE_FLUIDSYNTH=ON -DUSE_NETWORK=ON "
            "-DBUILD_DOCS=OFF -DBUILD_TESTING=ON"
        ).format(prefix=prefix, core5=core5, linguist=linguist)

    def build(self):
        apply_conandata_patches(self)
        env_part = self._env_part()
        args = self._configure_args()
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        src = os.path.abspath(self.source_folder)
        bld = os.path.abspath(self.build_folder)
        # configure：显式带 LD_LIBRARY_PATH（qmake 探测）、PKG_CONFIG_PATH
        # （fluidsynth.pc 修正版）与完整 Qt6 组件 -D 参数（E520 + 探索验证）。
        self.run(
            'cmake -E env {env} cmake -S {src} -B {bld} '
            '-DCMAKE_TOOLCHAIN_FILE={tc} -DCMAKE_BUILD_TYPE=Release {args}'.format(
                env=env_part, src=src, bld=bld, tc=toolchain, args=args
            ),
            env="conanbuild",
        )
        # build：lrelease/moc 等 Qt 工具需要 qtbase lib 与 libc++。
        # -j1：避免 HMDFS 上 make jobserver mkfifo 受限。
        self.run(
            'cmake -E env {env} cmake --build {bld} -j1'.format(
                env=env_part, bld=bld
            ),
            env="conanbuild",
        )
        # 上游 CTest：fileTest1/2/3 + rtTest + widgetsTest
        self.run(
            'cmake -E env {env} ctest --test-dir {bld} --output-on-failure -j1'.format(
                env=env_part, bld=bld
            ),
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 复用上游安装的自带 CMake config（lib/cmake/drumstick/），
        # 避免 CMakeDeps 对 cmake_find_mode=none 依赖（qtbase/qttools）
        # 生成 find_dependency 导致消费者 find_package 失败。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.components["file"].libs = ["drumstick-file"]
        self.cpp_info.components["file"].set_property(
            "cmake_target_name", "Drumstick::File"
        )
        self.cpp_info.components["rt"].libs = ["drumstick-rt"]
        self.cpp_info.components["rt"].set_property(
            "cmake_target_name", "Drumstick::RT"
        )
        self.cpp_info.components["widgets"].libs = ["drumstick-widgets"]
        self.cpp_info.components["widgets"].set_property(
            "cmake_target_name", "Drumstick::Widgets"
        )
