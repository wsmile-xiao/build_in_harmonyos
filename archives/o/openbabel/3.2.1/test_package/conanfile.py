#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy


class TestPackageConan(ConanFile):
    """openbabel 消费者测试：SMILES→InChI 转换断言。

    实质依赖被测包（R34）：
    - 实例化被测包核心转换 API OBConversion
    - SetInAndOutFormats("smi", "inchi") 同时验证格式插件加载链路
      （dlopen 插件 + 插件注册表 + inchi 库），任一环节失败均返回 False
    - ReadString/WriteString 断言乙醇 SMILES "CCO" 的 InChI 输出含
      "InChI=1S/C2H6O"（结构正确的硬断言，非 print-only）
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str, transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate(scope="run")
        CMakeToolchain(self).generate()

    def build(self):
        copy(self, "CMakeLists.txt", self.source_folder, self.build_folder)
        copy(self, "test.cpp", self.source_folder, self.build_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.skip("cross-build: 无法在本机执行目标二进制")
        # OHOS 忽略 DT_RUNPATH：运行时 .so（libopenbabel.so.8 / 插件 /
        # libinchi / libxml2）须经 LD_LIBRARY_PATH 解析。收集依赖图全部
        # libdir，用 shell 前缀直接注入（self.run 的 env 参数是 env 脚本
        # 文件名而非 VAR=VALUE 列表，故不走该机制）。
        ld = []
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.aggregated_components().libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if os.path.isdir(p) and p not in ld:
                    ld.append(p)
        ld_path = ":".join(ld)
        # 显式注入 BABEL_LIBDIR=包内插件目录：不依赖进程环境继承或编译期
        # OB_MODULE_PATH 回退，消除 build() 环境泄漏带来的不确定性（OHOS 下
        # 插件搜索仅认 BABEL_LIBDIR 或烘焙路径，显式指定最确定）
        ob_pkg = self.dependencies["openbabel"].package_folder
        babel_libdir = os.path.join(ob_pkg, "lib", "openbabel", "3.2.1")
        exe = os.path.join(self.build_folder, "test_package_exe")
        self.run(
            'LD_LIBRARY_PATH="{}" BABEL_LIBDIR="{}" "{}"'.format(ld_path, babel_libdir, exe))
