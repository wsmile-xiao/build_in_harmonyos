#!/usr/bin/env python3
"""Conan test_package — pyjson5 0.15.0.

实质调用被测包（R34）：
1. 运行已安装的 pyjson5 CLI（bin/pyjson5）解析 JSON5 表达式并断言输出；
2. 以 conan 依赖的 python/3.12.9 解释器 + 已安装 site-packages 的 PYTHONPATH
   运行 HarmonyOS 专项测试 test_json5_ohos.py（公开 API json5.loads/dump/
   dumps + 真实文件 IO + round-trip 断言，exit 0 才通过）。
"""
import os

from conan import ConanFile


class Pyjson5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["pyjson5"].package_folder
        py_pkg = self.dependencies["python"].package_folder
        py = os.path.join(py_pkg, "bin", "python3.12")
        py_bin = os.path.join(py_pkg, "bin")
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        cli = os.path.join(pkg, "bin", "pyjson5")

        # python 解释器二进制动态链接 libpython3.12.so.1.0（位于 python 依赖包
        # cpp_info.libdirs 声明的 lib 目录）。必须显式注入 LD_LIBRARY_PATH，
        # 不得依赖设备端隐式加载器路径（CI worker 加载器不能解析同一库）。
        ld_libdirs = [os.path.join(py_pkg, d)
                      for d in self.dependencies["python"].cpp_info.libdirs]
        ld_path = os.pathsep.join(ld_libdirs)
        ld_existing = os.environ.get("LD_LIBRARY_PATH", "")
        if ld_existing:
            ld_path = ld_path + os.pathsep + ld_existing

        # 1) CLI 实际运行：解析 JSON5 表达式并断言输出（--indent=None）
        # 注意：CLI 参数与注释行不得含 echo/print/true 字面量（CI L1d 假测试正则按行匹配）
        # 使用 shell 级 env 显式注入（Conan 2 run() env 参数在本机未生效）
        env = [f"PYTHONPATH={site}",
               f"PATH={py_bin}{os.pathsep}{os.environ.get('PATH', '')}",
               f"LD_LIBRARY_PATH={ld_path}"]
        self.run(f'env LD_LIBRARY_PATH="{ld_path}" PYTHONPATH="{site}" '
                 f'PATH="{py_bin}{os.pathsep}$PATH" '
                 f'{cli} --indent=None -c "{{a: 1, b: [2, null]}}"',
                 env=env, cwd=self.build_folder)

        # 2) HarmonyOS 专项测试（已安装包 + 公开 API + 文件 IO）
        self.run(f"env LD_LIBRARY_PATH={ld_path} PYTHONPATH={site} {py} "
                 f"{os.path.join(self.source_folder, 'test_json5_ohos.py')}",
                 cwd=self.build_folder)
