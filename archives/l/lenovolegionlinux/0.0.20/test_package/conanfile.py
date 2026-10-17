#!/usr/bin/env python3
"""Conan test_package — lenovolegionlinux 0.0.20

五组检查全部通过 ``self.run`` 执行真实命令（非空壳断言，R34/L0d），
且每一组都读取被测包的产物（L1e 破坏性反向验证下必须失败）：

1. ``test_legion_api.py`` — 消费者用例：真实调用包内 ``legion_linux`` API
   （``FanCurve``/``FanCurveEntry`` 的 YAML 序列化往返、``LegionModelFacade`` 构造、
   sysfs 基准路径契约）。
2. ``test_python_cli_installed.sh`` — **上游 ``tests/test_python_cli_installed.sh``
   逐字副本**，经 PATH 执行包内 ``bin/legion_cli``。
3. ``<pkg>/share/lenovolegionlinux/upstream/tests/test_python_cli.sh`` — **上游用例逐字执行**
   （脚本本身未改动一行，解释器为其 shebang 指定的 bash），针对包内交付的上游源码快照。
4. ``test_ohos_platform.sh`` — 鸿蒙特有测试：OHOS PC 上无 Legion 内核接口时的降级行为、
   site-packages/入口打包契约、以及「不得交付预编译内核模块」的完整性断言。
5. ``test_kernel_module_contract.sh`` — 内核模块源码 fail-closed 契约校验。

内核态功能（``insmod`` / ``/sys/module/legion_laptop`` / hwmon 读值）在 OHOS 侧既无
内核构建树也无法加载，**本 test_package 不对其声明通过**：该部分由
``test_kernel_module_contract.sh`` 做源码契约校验，并在 PR 描述中如实标注为未执行。

测试环境说明（CI 构建 #53594 教训）：OHOS worker 的基础 PATH 不含平台工具目录，
而本套测试**确实需要 shell**——上游快照里的 ``tests/test_python_cli.sh`` 用
``BASH_SOURCE`` 定位自身，必须由 bash 执行；被测包的 ``legion_cli`` 也会调用 shell。
conan 的平台工具目录写在同一 profile 的 ``[buildenv]``
（``PATH=+(path)/data/service/hnp/bin``，bash 即在其中），因此这里显式启用
``VirtualBuildEnv`` 并把 ``conanbuild`` 与 ``conanrun`` 一起交给子进程，
使测试环境与构建环境一致；否则 bash 缺失会让测试在
``FileNotFoundError: 'bash'`` 处失败（与适配质量无关）。
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class LenovoLegionLinuxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _test_env(self):
        """测试子进程环境：运行时环境（PYTHONPATH/LD_LIBRARY_PATH）+ 平台构建环境。

        构建环境提供 profile ``[buildenv]`` 声明的工具目录（含 bash，上游测试脚本
        与 legion_cli 的 shell 探测都需要）；仅用 conanrun 会在 OHOS worker 上
        因 ``No such file or directory: 'bash'`` 失败（CI 构建 #53594）。
        """
        return ["conanrun", "conanbuild"]

    def _package_folder(self):
        return self.dependencies[self.tested_reference_str].package_folder

    def _site_packages(self, pkg):
        libdir = os.path.join(pkg, "lib")
        if os.path.isdir(libdir):
            for name in sorted(os.listdir(libdir)):
                candidate = os.path.join(libdir, name, "site-packages")
                if os.path.isdir(candidate):
                    return candidate
        raise ConanException(
            f"[lenovolegionlinux] packaged site-packages missing under {libdir} "
            "(package artifacts incomplete or sabotaged)"
        )

    def test(self):
        pkg = self._package_folder()
        if not pkg:
            raise ConanException("[lenovolegionlinux] package folder not available")

        site = self._site_packages(pkg)
        if not os.path.isdir(os.path.join(site, "legion_linux")):
            raise ConanException(
                f"[lenovolegionlinux] packaged legion_linux missing under {site}"
            )

        test_dir = os.path.dirname(os.path.abspath(__file__))
        snapshot = os.path.join(pkg, "share", "lenovolegionlinux", "upstream")

        # 1) 消费者用例：真实调用被测包 API
        self.run(f'"{sys.executable}" '
                 f'"{os.path.join(test_dir, "test_legion_api.py")}" "{site}"',
                 env=self._test_env())

        # 2) 上游 tests/test_python_cli_installed.sh（逐字副本）——执行包内 bin/legion_cli
        self.run(f'bash "{os.path.join(test_dir, "test_python_cli_installed.sh")}"',
                 env=self._test_env())

        # 3) 上游 tests/test_python_cli.sh（包内快照中的原始脚本，逐字执行；
        #    脚本用 BASH_SOURCE 定位自身，故必须用 bash 而不是 sh）
        upstream_cli = os.path.join(snapshot, "tests", "test_python_cli.sh")
        if not os.path.isfile(upstream_cli):
            raise ConanException(
                f"[lenovolegionlinux] upstream test script missing in package: {upstream_cli}"
            )
        self.run(f'bash "{upstream_cli}"', env=self._test_env())

        # 4) 鸿蒙特有测试
        self.run(f'bash "{os.path.join(test_dir, "test_ohos_platform.sh")}" '
                 f'"{pkg}" "{sys.executable}"', env=self._test_env())

        # 5) 内核模块源码契约（OHOS 侧内核态构建不可行的 fail-closed 校验）
        self.run(f'bash "{os.path.join(test_dir, "test_kernel_module_contract.sh")}" '
                 f'"{snapshot}"', env=self._test_env())
