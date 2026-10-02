#!/usr/bin/env python3
"""Conan recipe — riscemu 2.2.7 (纯 Python 包, poetry-core).

HarmonyOS PC 适配：riscemu 是纯 Python 实现的 RISC-V 模拟器/调试器
(riscemu/ 包, 无 C/C++ 源码、无原生扩展、无编译产物), 因此不存在需要交叉
编译到 aarch64-linux-ohos 的目标代码 —— 交付物就是上游 Python 包本体加上它
完整的运行时依赖闭包, 原样铺进 package 目录。

运行时依赖 pyelftools>=0.30 / importlib-resources>=6.1.0 未在 OHPC 制品仓发布,
因此按本仓已合入的纯 Python 包既有做法 (airthings-ble/1.2.0、aiven-client/4.16.0、
rapt-ble/0.1.2) 由 pip 从已配置的 pypi.cnb.cool 镜像解析并 vendoring 进包的
site-packages, 不作为 conan requires 声明。

`--ignore-installed` 的作用：即使宿主解释器已经满足某个 requirement (例如
Python 3.12 自带 importlib_resources 的等价能力), 也强制把整个闭包重新展开到
package 内, 避免产物依赖构建机的环境状态。消费者只需把包的 site-packages 加进
PYTHONPATH 即可使用, 见 package_info()。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RiscemuConan(ConanFile):
    name = "riscemu"
    version = "2.2.7"
    description = "A basic RISC-V emulator"
    license = "MIT"
    homepage = "https://github.com/AntonLydike/riscemu"
    url = "https://github.com/AntonLydike/riscemu"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is a pure Python package, only OHOS/Linux targets are supported"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _site_packages(self, base):
        ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join(base, "lib", ver, "site-packages")

    def build(self):
        apply_conandata_patches(self)
        stage = os.path.join(self.build_folder, "stage")
        python = sys.executable
        # pip install . 现场构建 (poetry-core 后端); 运行时依赖由 pip 从
        # pypi.cnb.cool 镜像解析。不使用 --no-build-isolation：让 pip 自建
        # 隔离构建环境并从镜像取 poetry-core（与 airthings-ble/aiven-client 一致）。
        self.run(
            f"{python} -m pip install . --prefix={stage} --ignore-installed",
            cwd=self.source_folder,
        )
        site = self._site_packages(stage)
        if not os.path.isdir(os.path.join(site, "riscemu")):
            raise ConanException(f"riscemu package missing under {site}")
        # 依赖闭包必须真的落到 stage 里（R36 的证据面：产物自带依赖，不靠环境）。
        for dep in ("elftools", "importlib_resources"):
            if not os.path.isdir(os.path.join(site, dep)):
                raise ConanException(f"runtime dependency {dep} missing under {site}")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        if not os.path.isdir(stage):
            raise ConanException(f"stage directory not found: {stage}, nothing to package")
        for item in os.listdir(stage):
            src = os.path.join(stage, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=stage, dst=self.package_folder)

    def package_info(self):
        # 纯 Python 包：无头文件/库目录，只需把 site-packages 暴露给消费者。
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        site = self._site_packages(self.package_folder)
        self.runenv_info.append_path("PYTHONPATH", site)
        # console script (poetry scripts.riscemu -> riscemu.__main__:main) 落在
        # 包的 bin/ 下，直接进 PATH，使 `riscemu prog.asm` 与上游一致可用。
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            self.runenv_info.append_path("PATH", bindir)
        self.output.info(f"riscemu site-packages: {site}")
