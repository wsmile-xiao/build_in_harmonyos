#!/usr/bin/env python3
"""Conan test_package — bambam 1.4.1.

实质调用被测包（R34）：
1. 运行已安装的 bin/bambam --help：argparse 在 pygame.init 之前解析并正常
   退出 0（无显示也能跑，SDL dummy 环境）；
2. 以 conan 依赖的 python/3.12.9 解释器 + SDL dummy 运行鸿蒙专项测试
   test_bambam_ohos.py（import bambam 冒烟 + 包布局断言 + 上游数据目录发现
   逻辑 + 可选 boot 冒烟，SDL dummy 限制如实上报，E212 有静态降级）；
3. 运行上游 4 个 StreamChecker 单元测试（复制 test_e2e.py + test_e2e_test.py
   到 test_package/，python3 -m unittest test_e2e_test -v，不 import pygame）。

注意：本 test() 全部为真实执行（--help / SDL dummy 冒烟 / 上游 unittest），
不使用空壳 shell 命令；SDL dummy 消费端环境变量由测试脚本注入。
"""
import os

from conan import ConanFile


class BambamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ld_library_path(self):
        # python 解释器二进制动态链接 libpython3.12（python 依赖包 libdirs）
        # + pygame 依赖包捆绑 SDL 运行库（pygame/.libs）。必须显式注入
        # LD_LIBRARY_PATH，不得依赖设备端隐式加载器路径（CI worker 加载器
        # 不能解析同一库，pyjson5 CI 返工教训）。
        dirs = [os.path.join(self.dependencies["python"].package_folder, d)
                for d in self.dependencies["python"].cpp_info.libdirs]
        pygame_pkg = self.dependencies["pygame"].package_folder
        pygame_site = os.path.join(pygame_pkg, "lib", "python3.12",
                                   "site-packages")
        dirs.append(os.path.join(pygame_site, "pygame", ".libs"))
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        if existing:
            dirs.append(existing)
        return os.pathsep.join(dirs)

    def test(self):
        pkg = self.dependencies["bambam"].package_folder
        py_pkg = self.dependencies["python"].package_folder
        pygame_pkg = self.dependencies["pygame"].package_folder
        py = os.path.join(py_pkg, "bin", "python3.12")
        py_bin = os.path.join(py_pkg, "bin")
        site_bambam = os.path.join(pkg, "lib", "python3.12", "site-packages")
        site_pygame = os.path.join(pygame_pkg, "lib", "python3.12",
                                   "site-packages")

        ld_path = self._ld_library_path()
        pypath = os.pathsep.join([site_bambam, site_pygame])
        env = [f"PYTHONPATH={pypath}",
               f"PATH={py_bin}{os.pathsep}{os.environ.get('PATH', '')}",
               f"LD_LIBRARY_PATH={ld_path}"]
        sdl_env = ("SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "
                   "PYGAME_HIDE_SUPPORT_PROMPT=1 PYTHONDONTWRITEBYTECODE=1")

        # 1) CLI 实际运行：bin/bambam --help（argparse 退出 0）
        cli = os.path.join(pkg, "bin", "bambam")
        self.run(f'env LD_LIBRARY_PATH="{ld_path}" PYTHONPATH="{pypath}" '
                 f'PATH="{py_bin}{os.pathsep}$PATH" {sdl_env} '
                 f'{cli} --help',
                 env=env, cwd=self.build_folder)

        # 2) 鸿蒙专项测试（已安装包 + SDL dummy 冒烟 + 布局 + 数据发现逻辑）
        self.run(f'env LD_LIBRARY_PATH="{ld_path}" PYTHONPATH="{pypath}" '
                 f'PATH="{py_bin}{os.pathsep}$PATH" {sdl_env} '
                 f'BAMBAM_PKG_ROOT={pkg} BAMBAM_SITE={site_bambam} {py} '
                 f'{os.path.join(self.source_folder, "test_bambam_ohos.py")}',
                 cwd=self.build_folder)

        # 3) 上游 4 个 StreamChecker 单元测试（test_e2e_test.py 不 import pygame）
        self.run(f'env LD_LIBRARY_PATH="{ld_path}" PYTHONPATH="{pypath}" '
                 f'PATH="{py_bin}{os.pathsep}$PATH" {py} -m unittest '
                 f'test_e2e_test -v',
                 cwd=self.source_folder)
