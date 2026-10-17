#!/usr/bin/env python3
"""Test package for iroffer 1.4.b03 — R34/PF3: 必须真正执行被测包的二进制。

iroffer 是常驻 IRC 守护进程，CI 里没有 IRC 服务器可连，所以不测"上线传文件"，
而是驱动它自己确定性的命令行代码路径 + 让第二个二进制跑一次**真实数据往返**
（每条都落在 iroffer_main.c / convertxdccfile.c 的真实解析分支里，不是打印字符串的空壳）：

  1. iroffer -v                 版本分支（PCL_SHOW_VERSION）
  2. iroffer                    无配置文件的参数校验分支
  3. iroffer -h                 未识别选项分支（上游对未知选项只告警后打 usage）
  4. iroffer -d -n -s cfg       读配置 → 完整性校验（不完整配置以退出码 1 收场）
  5. convertxdccfile            无参 usage
  6. convertxdccfile -x -s      .xdcc → .state 真转换，按上游写 state 的那段代码
                                （src/iroffer_statefile.c:93-94/223-234/246-267、Configure:8/21）
                                对产物做**偏移级逐字节**校验：头 8 字节 magic+格式版本、
                                版本条目 tag/length、偏移 16 起的 "iroffer v1.4.b03 ["
                                （端到端自证；⛔ 不对二进制文件用 grep——同一份产物上
                                GNU grep 3.12 命中而 toybox 0.8.12 不命中且不报错，
                                详见 test.sh 头部与 notes.md「CI 复现与断言形态整改」节）
  7. convertxdccfile 坏输入      解析器失败分支

`iroffer -c`（口令生成器）因退出码随有无控制终端变化（1 / timeout 124）而**不作为断言**，
理由与实测数据记在 test.sh 头部与 MANIFEST.yml 里。

共 16 条断言，逐条计数、由 test.sh 的退出码汇总；本 test() 用 self.run 真跑，不吞返回值。
"""
import os

from conan import ConanFile


class IofferTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["iroffer"].package_folder
        iroffer_bin = os.path.join(pkg, "bin", "iroffer")
        convert_bin = os.path.join(pkg, "bin", "convertxdccfile")
        for path in (iroffer_bin, convert_bin):
            if not os.path.exists(path):
                raise Exception(f"packaged binary missing: {path}")

        test_script = os.path.join(self.source_folder, "test.sh")
        # 计数以 test.sh 自己打印的 "PASS n/n" 为准，不在这里重复写死数字。
        self.run(
            f'IROFFER_BIN="{iroffer_bin}" '
            f'CONVERTXDCCFILE_BIN="{convert_bin}" '
            f'bash "{test_script}"',
            env="conanrun",
        )
        self.output.info("iroffer + convertxdccfile executed via test.sh")
