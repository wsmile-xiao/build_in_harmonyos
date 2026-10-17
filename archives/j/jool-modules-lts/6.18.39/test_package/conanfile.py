#!/usr/bin/env python3
"""Conan test_package — jool-modules-lts 6.18.39

四组检查全部通过 ``self.run`` 执行真实命令（非空壳断言，R34/L0d），且每一组都读取
被测包的产物（L1e 破坏性反向验证下必须失败）：

1. ``test_cli_contract.sh`` — 上游 CLI 真实行为契约：执行包内 ``bin/jool`` /
   ``bin/jool_siit`` / ``bin/joold`` 的 ``--help`` / ``--usage`` / ``--version``
   入口，并验证「内核模块缺失时的优雅降级」（-ESRCH 契约：打印可行动的错误提示、
   非零退出、不崩溃）。
2. ``test_ohos_platform.sh`` — 鸿蒙特有测试：OHOS 交付布局（bin/ 三件套 + 手册页）、
   commands.json 入口可经 PATH 发现、**不得交付预编译 .ko/.o**、上游源码快照
   完整性、以及 OHOS 上内核模块永不可加载时的 fail-closed 降级行为。
3. ``test_kernel_module_contract.sh`` — 内核模块源码快照的 fail-closed 契约校验
   （Kbuild obj-m ×3、MODULE_LICENSE、module_init/exit、/lib/modules 内核树依赖、
   dkms.conf、无预编译产物）。
4. ``test_upstream_block_preconditions.sh`` — 上游 36 个测试脚本逐脚本阻塞前置
   fail-closed 审计 + 2 个带非 root 快速退出的上游脚本**真实执行**（预期以
   root 前置阻塞退出；若某脚本的上游形态变得用户态可跑，审计立即失败，强制重评）。

内核态功能（insmod / modprobe / netns 报文注入）在 OHOS 侧既无内核构建树也无法
加载，**本 test_package 不对其声明通过**：内核边界由第 3 组做源码契约校验，第 4
组做逐脚本阻塞证据，并在 PR 描述中如实标注。

测试环境说明（lenovolegionlinux CI #53594 教训）：OHOS worker 的基础 PATH 不含
平台工具目录（bash 在 profile [buildenv] 的 /data/service/hnp/bin 里），故显式
启用 ``VirtualBuildEnv`` 并把 ``conanbuild`` 与 ``conanrun`` 一起交给子进程。
"""

import os

from conan import ConanFile
from conan.errors import ConanException


class JoolModulesLtsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _test_env(self):
        # conanrun：包产物环境；conanbuild：profile [buildenv] 的平台工具目录（含 bash）
        return ["conanrun", "conanbuild"]

    def test(self):
        # R32：平台判断用 in，不用 ==
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.info(
                f"skip runtime test on {self.settings.os} (cross-compiled)")
            return

        pkg = self.dependencies[self.tested_reference_str].package_folder
        if not pkg:
            raise ConanException("[jool-modules-lts] package folder not available")
        snapshot = os.path.join(pkg, "share", "jool-modules-lts", "upstream")
        test_dir = os.path.dirname(os.path.abspath(__file__))

        # 1) 上游 CLI 行为契约（执行包内真实二进制）
        self.run(f'bash "{os.path.join(test_dir, "test_cli_contract.sh")}" "{pkg}"',
                 env=self._test_env())

        # 2) 鸿蒙特有测试（OHOS 交付契约 + 无内核模块时的降级行为）
        self.run(f'bash "{os.path.join(test_dir, "test_ohos_platform.sh")}" "{pkg}"',
                 env=self._test_env())

        # 3) 内核模块源码快照 fail-closed 契约
        self.run(f'bash "{os.path.join(test_dir, "test_kernel_module_contract.sh")}" '
                 f'"{snapshot}"', env=self._test_env())

        # 4) 上游 36 脚本逐条阻塞前置审计 + 2 个 root-bail 脚本真实执行
        self.run(f'bash "{os.path.join(test_dir, "test_upstream_block_preconditions.sh")}" '
                 f'"{os.path.join(test_dir, "upstream-block-map.tsv")}" '
                 f'"{os.path.join(snapshot, "test")}"', env=self._test_env())
