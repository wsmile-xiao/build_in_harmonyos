#!/usr/bin/env python3
"""Conan test_package — rtags L1 功能测试（R34：实质调用被测包 API/二进制）。

测试逻辑见 run_test.sh（独立测试源文件，满足 L0c）：
1. smoke：rc/rdm 可执行并可报版本（OHOS 签名+动态链接正确性）；
2. 功能：启动 rdm 守护进程（TCP 回环）→ rc -J 装载 compile_commands.json →
   libclang 真实解析索引 test_project.c → rc -R 引用查询断言。

平台说明：OHOS 设备 SELinux 禁止 AF_UNIX bind（/dev/shm errno 13、HMDFS errno 1），
统一走 TCP 回环（rdm --tcp-port / rc --socket-address），配合补丁 0003/0005。
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class RtagsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        env = VirtualRunEnv(self)
        env.environment().prepend_path("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.environment().define_path("HOME", self.build_folder)
        env.environment().define("TEST_BINDIR", self.dependencies["rtags"].cpp_info.bindirs[0])
        # 运行时产物（.rtags/rdm.log 等）写临时目录，不污染 test_package 源目录
        projdir = tempfile.mkdtemp(prefix="rtags-e2e-", dir=os.environ.get("TMPDIR") or None)
        env.environment().define("TEST_PROJDIR", projdir)
        env.generate("conanrun")

        script = os.path.join(self.source_folder, "run_test.sh")
        self.run("bash '%s'" % script, env="conanrun")
