#!/usr/bin/env python3
"""pistache test_package —— 消费者视角验证（L1）。

上游 Meson 安装只提供 pkg-config 元数据（lib/pkgconfig/libpistache.pc），不生成 CMake
config，因此消费者侧走 pkg-config 而非 find_package。测试脚本真实编译并运行一个调用
pistache 公共 API 的消费者程序，断言编译退出码、运行退出码与输出内容。

pkg-config 搜索路径与 C++ 编译器以命令行参数传给脚本，不经 conan 的 env 传递，
避免 run(env=) 的覆盖语义造成变量丢失。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PistacheTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # 本仓适配目标是本机原生构建（build = host），正常不走到这里；
            # 保留以免交叉编译场景下误报失败。
            self.output.info("target 不可运行（交叉编译场景），跳过消费者程序执行")
            return

        script = os.path.join(self.source_folder, "test_pistache.sh")
        if not os.path.isfile(script):
            raise ConanException(f"消费者测试脚本缺失: {script}")

        # 安装树里 Meson 装好的 .pc 在 <package_folder>/lib/pkgconfig；
        # conan 的 PkgConfigDeps 也会在 generators 目录再生成一份，两者都提供给 pkg-config。
        search_paths = [self.generators_folder]
        pkg_folder = self.dependencies["pistache"].package_folder
        if pkg_folder:
            search_paths.append(os.path.join(pkg_folder, "lib", "pkgconfig"))
        pkg_config_path = os.pathsep.join(p for p in search_paths if p)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compiler_executables.get("cpp") or compiler_executables.get("cxx") or ""

        self.output.info(f"PKG_CONFIG_PATH={pkg_config_path}")
        self.output.info(f"CXX={cxx or '<默认 c++>'}")

        self.run(f'bash "{script}" "{pkg_config_path}" "{cxx}"')
