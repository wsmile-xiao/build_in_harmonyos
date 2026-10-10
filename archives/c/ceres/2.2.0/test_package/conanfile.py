#!/usr/bin/env python3
"""Conan test_package for ceres 2.2.0 —— 消费者测试（真实编译+链接；原生构建下 ctest 真实执行）。

交叉编译（本机 x86-64 → OHOS aarch64）时：OHOS SDK 不随附设备端 musl 动态加载器，本机 QEMU
执行动态 aarch64 OHOS 产物会段错误；本配方的消费者在交叉环境下仍做**真实编译 + 真实链接**，
并由配套脚本做**全静态链接 + QEMU 真跑**作为独立证据（scripts/ohos/verify-ceres-runtime.sh）。
设备端原生构建（官方 CI aarch64 worker）下 test() 直接以 ctest 真实执行。

依赖解析：test_package 只 requires(ceres)，Eigen 作为传递依赖由 CMakeDeps 生成的
CeresConfig.cmake 自动 find_dependency(Eigen3) 带出（recipe 里声明了
cpp_info.requires = ["eigen::eigen"]）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class CeresTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明 Eigen：ceres 的公共头文件直接 #include <Eigen/Core>，消费者编译时必须有
        # Eigen 的头文件目录。只依赖传递边时 CMakeDeps 不会为 Eigen 生成 config，
        # 头文件目录也可能拿到相对路径（实测 'Eigen/Core' file not found 就是这个原因）。
        self.requires("eigen/3.4.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CERES_PACKAGE_FOLDER"] = self.dependencies["ceres"].package_folder.replace("\\", "/")
        # 回退路径（找不到 Ceres 配置包时）用：把所有依赖的 include 目录以**绝对路径**传过去。
        inc = []
        for dep in self.dependencies.values():
            try:
                for d in dep.cpp_info.aggregated_components().includedirs:
                    if not d:
                        continue
                    full = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                    full = full.replace("\\", "/")
                    if full not in inc:
                        inc.append(full)
            except Exception:  # noqa: BLE001 - 单个依赖取不到不影响整体
                continue
        tc.variables["DEP_INCLUDE_DIRS"] = ";".join(inc)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ctest_bin(self):
        """定位 ctest：PATH → 常见 HNP/SDK 目录（CI worker 的 PATH 不一定含 ctest）。"""
        found = shutil.which("ctest")
        if found:
            return found
        for cand in (
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake/bin/ctest",
            "/system/bin/ctest",
            "/usr/bin/ctest",
            "/usr/local/bin/ctest",
        ):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return "ctest"

    def test(self):
        if not can_run(self):
            self.output.info(
                "交叉编译环境：不执行动态 aarch64 产物（SDK 无设备端 musl 加载器）；"
                "本机另以全静态链接 + QEMU 真跑消费者测试作为证据。"
            )
            return
        env = Environment()
        env.define("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            # env="conanrun" 让聚合运行环境生效（CI worker 上 C++ 运行库只经该环境可达）
            self.run(f'"{self._ctest_bin()}" --output-on-failure',
                     cwd=self.build_folder, env="conanrun")
