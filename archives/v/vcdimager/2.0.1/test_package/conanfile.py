import json
import os
import re

from conan import ConanFile


class VcdimagerTestConan(ConanFile):
    """test_package for vcdimager 2.0.1 — 安装后的 CLI 逐个真跑。

    vcdimager 是 application 包：交付物是 7 个命令行程序
    （vcdimager / cdxa2mpeg / vcd-info / vcdxbuild / vcdxgen / vcdxrip / vcdxminfo）。
    conan-init 生成的空壳 test.c（只 print、无条件 return 0）证不到任何东西，
    PF3/R34 必拦 —— 换成 test.sh 的真断言。该空壳 test.c 与配套的 CMakeLists.txt
    （add_executable/add_test）已按 09-26 审查意见一并删除，本 test_package 内不再
    并存第二条测试入口，test() 也只执行 test.sh 一条命令。

    断言条数**不写死**：由 _count_assertions() 从同目录的 test.sh 里现数
    （run / grep_check 各计 1 条），这样 HMBS_TEST_PACKAGE_RESULT 的 discovered
    永远与实跑的 harness 同源；上一版把 14 写死，test.sh 改成 17 条后
    第 12 轮实拍 marker 报 discovered=14 而 test.sh 汇总行报 17 项，
    属"机器可读数字与证据不同源"，故改成推导式。

    passedCount 的口径：test.sh 自己累计 FAILED 并在非零时 exit 1，
    所以 conan 这一层「脚本正常返回」等价于「全部断言通过」；
    一旦失败则记 0，逐条读数留在同一份日志的 test.sh 输出里。

    上游 make check 的 8 项功能测试（含真调 vcdimager/vcdxbuild/vcdxrip 并比对
    .right 基准的 4 个 shell 驱动）在配方 build() 里真跑，读数由
    HMBS_UPSTREAM_TEST_RESULT 上报，不在这里重复计数。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _ASSERTION_RE = re.compile(r"^(?:run|grep_check)\s")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _count_assertions(self):
        """数 test.sh 里真正的断言调用行数（run / grep_check 各算 1 条）。"""
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        total = 0
        with open(script, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if self._ASSERTION_RE.match(line):
                    total += 1
        if total == 0:
            raise Exception("no assertions found in " + script)
        return total

    def test(self):
        # OHOS：/system/bin/sh (mksh) 不能执行 ELF，用工具链里确认存在的 bash 包装
        # （同 archives/a/adcli/0.9.2/test_package/conanfile.py 的处置）。
        bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = os.environ.get("CONFIG_SHELL", "sh")
        command = bash + " test.sh"
        discovered = self._count_assertions()
        # hmbs 硬门禁：marker 里的数字必须是 test_package 的真实条数（这里现数得来）。
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": discovered, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = discovered
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
