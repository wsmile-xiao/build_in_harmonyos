#!/usr/bin/env python3
"""Consumer test for the packaged keyd-application-mapper command.

运行方式说明（R34/L1e 破坏性反向验证）：
    不使用 ``can_run()`` 提前 return。CI 的 L1e 反向验证会以「仅 host profile」
    重新执行 ``conan test``，此时 build profile 是构建机默认 profile，与
    host(OHOS) 不同 → ``cross_building()`` 为真 → ``can_run()`` 为假 → test()
    直接返回、不执行任何断言，被判定为「假测试」。因此这里无条件执行消费者
    脚本：目标解释器由声明的 python 依赖提供，在 OHOS 主机上原生运行，在
    x86_64 构建机上经 binfmt/qemu 透明执行（与 build() 中的入口自检一致）。
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class KeydApplicationMapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        test_script = os.path.join(self.source_folder,
                                   "test_keyd_application_mapper.py")
        # R33: ``sys.executable`` 是运行 conan 的解释器，不是声明的 python
        # 依赖提供的那个。CI 干净 worker 上它指向 worker 自带解释器
        # (``/data/service/hnp/bin/python3``)，会因 libpython3.12.so 缺失以
        # exit 127 中止。这里始终用依赖自带的解释器；``env="conanrun"`` 已把
        # 该依赖的 ``lib/`` 放进 LD_LIBRARY_PATH。
        python = self._python_executable()
        self.run('"{}" "{}"'.format(python, test_script), env="conanrun")

    def _python_executable(self):
        """声明的 python 依赖提供的解释器（R33：不依赖裸环境变量）。"""
        py = self.dependencies["python"]
        candidate = os.path.join(py.package_folder, "bin", "python3")
        if not os.path.isfile(candidate):
            raise ConanException("python interpreter not found at {}".format(candidate))
        return candidate
