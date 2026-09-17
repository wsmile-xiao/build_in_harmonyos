#!/usr/bin/env python3
"""Conan test recipe — buffer 1.19：真实数据通路验证（消费者用例）。

buffer 是管道过滤器，没有 --version/--help（只有参数错误时打印 usage），
因此不能像普通 CLI 那样只做冒烟。5 条用例全部真实执行安装出来的 `buffer`
并对输出逐字节断言——否则 OHOS 上被沙箱拦截的 IPC 路径完全测不到（这正是本包
需要补丁的原因）。

用例实现在同目录的 `test_buffer.sh`（被 git 跟踪的测试源，满足 CI L0c；
纯内联断言会让干净检出上 L0c 判 fail）。所有临时文件写在 build_folder 下的
.buffer-selftest/，脚本结束（含失败）后自行删除；PASS/FAIL 行进入 conan 日志。
"""
import os

from conan import ConanFile


class TestBufferConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_buffer.sh")
        work = os.path.join(self.build_folder, ".buffer-selftest")
        # test_buffer.sh 内部做 5 条用例的逐字节断言；任一条失败即非零退出，
        # conan 会据此把 test_package 判为失败。
        self.run('sh "{}" "{}"'.format(script, work), env="conanrun")
