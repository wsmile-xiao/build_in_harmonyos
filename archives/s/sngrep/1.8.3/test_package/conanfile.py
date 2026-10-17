#!/usr/bin/env python3
"""sngrep 消费者测试（R34）：以使用者身份真实执行被测包安装的 sngrep 二进制。

三层断言，全部以真实执行 + 退出码/输出决定成败：
  1) `--version` 退出 0 且输出版本串 1.8.3（产物可运行）；
  2) `--help`    退出 0 且输出含 Usage（参数解析与 stdio 正常）；
  3) 功能断言：以 `-N`（no-interface，无需终端）解析本目录自带的真实 SIP pcap，
     断言 sngrep 解析出的 SIP 对话数 —— 覆盖被测程序的核心能力（SIP 流重建），
     而非仅版本/帮助这类冒烟输出。

输出统一写入产物目录下的临时子目录 `_consumer_out`，测试结束即删除，
不在源码树留下 version.out/help.out 之类残留文件。
"""
import base64
import os
import shutil

from conan import ConanFile


class SngrepTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        sngrep = os.path.join(dep.cpp_info.bindirs[0], "sngrep")

        outdir = os.path.join(self.build_folder, "_consumer_out")
        shutil.rmtree(outdir, ignore_errors=True)
        os.makedirs(outdir, exist_ok=True)

        # 夹具运行期解码（二进制不入仓：平台 git-am checkout 缺 --binary，见 ipip.pcap.b64/M23）
        pcap = os.path.join(self.build_folder, "ipip.pcap")
        b64src = os.path.join(self.source_folder, "ipip.pcap.b64")
        with open(b64src, "rb") as _fh:
            with open(pcap, "wb") as _out:
                _out.write(base64.b64decode(_fh.read()))

        try:
            # 断言集中在 test_smoke.sh（L0c 测试源文件）；sh 显式调用规避 HMDFS 无执行位
            self.run('sh "{0}" "{1}" "{2}" "{3}"'.format(
                os.path.join(self.source_folder, "test_smoke.sh"),
                sngrep, outdir, pcap), env="conanrun")
        finally:
            shutil.rmtree(outdir, ignore_errors=True)
            if os.path.exists(pcap):
                os.remove(pcap)
        print("sngrep consumer test PASSED (version/help/pcap-dialog-count, via test_smoke.sh)")
