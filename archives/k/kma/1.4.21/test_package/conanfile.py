#!/usr/bin/env python3
"""Conan test_package for kma 1.4.21 (executable package).

消费者视角的真实行为验证：用被打包出来的 kma 可执行文件建一个真实模板库，
再用上游自带的 -mmap 非 SysV 路径做真实比对，并逐字段核对结果数值。
R34/L1e：测试通过 bin/ 里的绝对路径调用被测包产物，一旦产物被搬走
（CI 的 L1e 破坏性反向验证就是干这个的）本测试必然失败，因此它确实依赖
被测包，不是空壳。

工作目录：每次跑一个唯一子目录，放在 $TMPDIR，没有 $TMPDIR 时放 ~/tmp
（与 CI 自身口径一致，见 ci/conan/build_and_test.sh 的 l1e_backup 目录）。
不落在这棵 checkout 里，是因为设备 /tmp 只读、而 archives 树内不能留产物
（root .gitignore 没有覆盖本测试的输出名，留在 test_package 下会污染 PR）。

上游没有任何注册测试（kma 1.4.21 的 Makefile 只有 all/kma/kma_index/
kma_shm/kma_update/libkma.a/clean 七个真目标 + 56 条 .o 依赖规则（实测：上游 1.4.21 Makefile 列首目标行 63 行 = 真目标 7 + .o 规则 56）；
无 check/test 目标；跨框架 grep 与目录 find 均 0 命中）——详见
test_package/MANIFEST.yml 与 notes.md 的清点原始命令。
"""

import os
import tempfile

from conan import ConanFile


class KmaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        here = os.path.dirname(os.path.abspath(__file__))
        pkg = self.dependencies["kma"].package_folder
        kma = os.path.join(pkg, "bin", "kma")
        script = os.path.join(here, "test_kma.py")
        # 与 CI 同口径的临时区：$TMPDIR 优先，退到 ~/tmp（设备 /tmp 只读）
        base = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        ws = tempfile.mkdtemp(prefix="kma-consumer-", dir=base)
        self.run('python3 "%s" "%s" "%s" "%s" "%s"'
                 % (script, kma,
                    os.path.join(here, "db.fa"),
                    os.path.join(here, "query.fa"),
                    ws),
                 env="conanrun")
