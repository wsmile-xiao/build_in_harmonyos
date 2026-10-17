#!/usr/bin/env python3
"""Conan test_package for libdrumstick 2.10.0.

消费者视角验证：链接 Drumstick::File 与 Drumstick::RT（上游自带的
drumstick-config.cmake IMPORTED targets），调用 drumstick::file::QSmf
写/读 SMF 流、drumstick::rt::BackendManager 枚举后端，验证真实 API 可用。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

_OHOS_SDK_LLVM_LIB = os.environ.get(
    "OHOS_SDK_LLVM_LIB",
    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
)


class LibdrumstickTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeToolchain 在此手动实例化（注入 Qt6 与 drumstick 组件路径）。
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qt5compat = self.dependencies["qt5compat"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        pkg = self.dependencies[self.tested_reference_str].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": ";".join(
                    p.replace("\\", "/")
                    for p in (qtbase, qt5compat, qttools, pkg)
                ),
                "Qt6_DIR": os.path.join(qtbase, "lib", "cmake", "Qt6").replace("\\", "/"),
                "Qt6Core5Compat_DIR": os.path.join(
                    qt5compat, "lib", "cmake", "Qt6Core5Compat"
                ).replace("\\", "/"),
                "Qt6LinguistTools_DIR": os.path.join(
                    qttools, "lib", "cmake", "Qt6LinguistTools"
                ).replace("\\", "/"),
                "drumstick_DIR": os.path.join(
                    pkg, "lib", "cmake", "drumstick"
                ).replace("\\", "/"),
            }
        )
        tc.generate()
        # 运行期库路径：qtbase 动态库 + OHOS SDK libc++_shared.so + 被测包库
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH",
            os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos"),
        )
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH",
            os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos", "c++"),
        )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_ld_library_path(self):
        """test() 运行期完整 LD_LIBRARY_PATH：
        conanrun 自动聚合的依赖 lib 目录 + OHOS SDK libc++_shared.so 目录。
        """
        qtbase = self.dependencies["qtbase"].package_folder
        qt5compat = self.dependencies["qt5compat"].package_folder
        qttoo = self.dependencies["qttools"].package_folder
        fs = self.dependencies["fluidsynth"].package_folder
        pkg = self.dependencies[self.tested_reference_str].package_folder
        paths = [
            os.path.join(pkg, "lib"),
            os.path.join(qtbase, "lib"),
            os.path.join(qt5compat, "lib"),
            os.path.join(qttoo, "lib"),
            os.path.join(fs, "lib"),
            os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos"),
            os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos", "c++"),
        ]
        uniq = list(dict.fromkeys(paths))
        return ":".join(uniq)

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_libdrumstick executable directory was not produced")
        cmd = os.path.join(bindirs[0], "test_libdrumstick")
        if not os.path.isfile(cmd):
            raise RuntimeError(
                "test_libdrumstick executable was not produced: {}".format(cmd)
            )
        # E298: 显式注入完整 LD_LIBRARY_PATH（含 SDK libc++），避免
        # conanrun 聚合环境缺路径导致 Qt6Core/drumstick 库加载失败。
        # DRUMSTICKRT：BackendManager 默认插件搜索路径基于可执行文件
        # 相对路径推导，test_package 中不命中；显式指向被测包插件目录。
        pkg = self.dependencies[self.tested_reference_str].package_folder
        plugins = os.path.join(pkg, "lib", "drumstick2")
        self.run(
            'env LD_LIBRARY_PATH="{}" DRUMSTICKRT="{}" {} --full'.format(
                self._run_ld_library_path(), plugins, cmd
            ),
            env="conanrun",
        )