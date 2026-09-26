#!/usr/bin/env python3
"""Conan test_package for cffi 2.1.1 — consumer-side check (R34 真实 API).

以消费者视角使用**已打包**的 cffi：不仅 import 校验，还真实调用 CFFI 的
公开 API（FFI/cdef/new/from_buffer/回调/结构体等 **ABI 模式**），以证明
C 扩展 `_cffi_backend` 确实可用。
（**API/verify 模式刻意不断言**：Python >= 3.12 上它要求运行期可用 setuptools，
而 setuptools 并非本包交付契约、也未发布到 ohpcd——写成断言会把"消费者环境
没装 setuptools"误报成"包坏了"。）

env="conanrun" 注入是必需的：包侧 package_info() 用 runenv_info 声明了
PYTHONPATH，裸 subprocess 会丢失该注入。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class CffiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cffi 在运行期 import pycparser（cparser.py）。显式声明使该依赖
        # 确定性地进入本测试图并带上 package_folder（实测仅作为被测算的
        # 传递依赖时，节点存在但 package_folder 为 None）。
        self.requires("pycparser/3.0")

    def test(self):
        pkg = self.dependencies["cffi"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")

        # 载荷完整性：纯 Python 层 + C 扩展缺一不可
        if not os.path.isfile(os.path.join(site, "cffi", "__init__.py")):
            raise ConanException(f"cffi python payload incomplete: {site}")
        exts = [f for f in os.listdir(site) if f.startswith("_cffi_backend")]
        if not exts:
            raise ConanException(
                f"cffi C extension (_cffi_backend*.so) missing under {site}")

        script = os.path.join(os.path.dirname(__file__), "test_cffi.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_cffi.py missing: {script}")

        # cffi 在**运行期** `import pycparser`（cparser.py；pyproject.toml:
        # dependencies = ["pycparser; implementation_name != 'PyPy'"]），故
        # 消费者进程必须同时拿到该依赖的 site-packages —— 包侧 package_info()
        # 的 PYTHONPATH 只含 cffi 自身，不含依赖（aiohttp 教训）。
        paths = [site]
        dep = self.dependencies.get("pycparser")
        if dep is None:
            raise ConanException("missing dependency: pycparser")
        dsite = os.path.join(dep.package_folder, "lib", "python3.12",
                             "site-packages")
        if not os.path.isdir(dsite):
            raise ConanException(f"pycparser site-packages missing: {dsite}")
        paths.append(dsite)
        os.environ["PYTHONPATH"] = os.pathsep.join(paths)

        self.run(f'python3 "{script}" "{site}"', env="conanrun")
