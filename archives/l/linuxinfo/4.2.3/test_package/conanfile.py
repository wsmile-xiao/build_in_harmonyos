#!/usr/bin/env python3
"""test_package for linuxinfo 4.2.3 — 消费者视角的功能测试 (R34).

linuxinfo 是一个"读 /proc + uname 然后打印系统摘要"的命令行工具，所以实质测试
就是**以使用者身份真的跑它**：退出码 + 输出内容双断言。上游没有测试套件
（test_package/MANIFEST.yml 里有逐条清点命令与命中数），因此功能面全部由这里承担。

OHOS 适配的直接回归点在 TC-05：上游 GetSystemLibcInfo() 对三个 .weak glibc 版本
符号做了无空指针保护的三选一，musl 上一个都不导出 → 原码会读地址 0 SIGSEGV
（139/SIGSEGV）。patches/0002 补了守卫，TC-05 以真机 /proc 无参运行来把它钉住。

解释器：OHOS 上没有 /bin/bash、/usr/bin/bash（实测 MISS），只有 /bin/sh
(→/system/bin/sh)；/data/service/hnp/bin/bash 存在。这里优先用探测到的 bash，
退回 /bin/sh，两者都不在时让 self.run 直接失败——绝不硬编码不存在的路径。
test.sh 本身写成严格 POSIX sh，两条路径都能跑。
"""
import os
import shutil

from conan import ConanFile


class LinuxinfoTestConan(ConanFile):
    """跑打包后的 linuxinfo 二进制并断言其真实输出。"""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _shell(self):
        # 不猜路径：按可达性挑一个确实存在的解释器。
        env = os.environ.get("CONFIG_SHELL")
        if env and os.path.isfile(env) and os.access(env, os.X_OK):
            return env
        for cand in ("/bin/sh", "/data/service/hnp/bin/bash"):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return shutil.which("sh") or "/bin/sh"

    def test(self):
        # PF3: test() 必须经 self.run 真执行被测包，空壳会被 L1d 判假。
        self.run(f"{self._shell()} test.sh", env="conanrun")
