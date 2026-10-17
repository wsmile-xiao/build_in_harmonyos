#!/usr/bin/env python3
"""test_package — malint 0.2 消费者验证

R34: test 必须实质调用被测包（禁止空壳）。真实断言在
test_package/test_malint.sh（L0c 测试源文件）：
1. 安装后的 bin/malint 存在且为 ELF；
2. malint --help 退出 0；
3. 上游官方样本 frame-short.in（base64 内嵌于脚本）以 `-N3`
   （上游 frame-short.test 的 flags）运行，输出与参考
   frame-short.log 关键行一致（帧头参数/缺字节报告/帧计数）。
交叉编译无法运行时降级为 ELF 魔数检查。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class MalintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["malint"].package_folder
        malint_bin = os.path.join(package_folder, "bin", "malint")
        assert os.path.isfile(malint_bin), f"malint binary not found: {malint_bin}"

        if not can_run(self):
            with open(malint_bin, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "malint is not an ELF binary"
            self.output.info(f"malint ELF binary exists: {malint_bin}")
            return

        test_script = os.path.join(self.recipe_folder, "test_malint.sh")
        # 设备 /bin/sh 可能处于不可执行状态：优先 PATH 中 bash（job 环境
        # 提供的入口可直接解释脚本），回退 sh；解释器直接执行脚本文件，
        # 不依赖脚本自身执行位（HMDFS E046/E087）。
        shell = "bash" if shutil.which("bash") else "sh"
        self.run(f'{shell} "{test_script}" "{malint_bin}"', env="conanrun")
        self.output.info("malint 0.2 consumer validation PASSED")
