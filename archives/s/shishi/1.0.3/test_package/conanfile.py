#!/usr/bin/env python3
"""Consumer test for shishi 1.0.3 (L1, run by `conan create`)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ShishiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS 目标在设备/CI worker 上直接运行；其余平台沿用 can_run 判定。
        if not (str(self.settings.os) == "OHOS" or can_run(self)):
            return
        # 防御 E019：OHOS 上 conanrun 环境可能省略 LD_LIBRARY_PATH，而被测包
        # 的工具与消费者程序都 DT_NEEDED 依赖 libgcrypt/libtasn1（构建机缓存
        # 内的共享库）。显式把包自身 lib/ 与全部依赖 libdir 前置注入本进程，
        # 子进程继承。
        dirs = []
        pkg_folder = self.dependencies["shishi"].package_folder
        for sub in ("lib", "lib64"):
            path = os.path.join(pkg_folder, sub)
            if os.path.isdir(path):
                dirs.append(path)
        for _, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                if path not in dirs and os.path.isdir(path):
                    dirs.append(path)
        if dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                dirs + ([existing] if existing else []))
            self.output.info(
                "LD_LIBRARY_PATH={}".format(os.environ["LD_LIBRARY_PATH"]))
        # 1) 消费者 C 程序：真实链接 libshishi/libshisa 并断言 4 项 API 行为。
        #    cwd 显式指到 build 目录（gitignore 的 build/ 内）：断言 4 会在当前
        #    目录写 tshisa.conf 与 tshisa-db/，不能落进提交面。注意 self.cpp.build
        #    是 _Component（只有 bindirs 等），布局目录用 ConanFile.build_folder。
        consumer = os.path.join(self.cpp.build.bindirs[0], "test_shishi")
        self.run(consumer, env="conanrun", cwd=self.build_folder)
        # 2) 打包进来的 5 个命令行工具按包内绝对路径冒烟（R34：真实依赖被测包）
        script = os.path.join(self.source_folder, "test_shishi_tools.sh")
        self.run('sh "{}" "{}"'.format(script, pkg_folder), env="conanrun")
